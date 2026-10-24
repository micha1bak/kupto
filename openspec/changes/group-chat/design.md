# Design

## Context

Czat asystenta to dziś jeden wątek na użytkownika w gospodarstwie: `chat_messages` z `user_id` i `household_id`, `GET/DELETE /api/chat/messages` filtrują po obu. Odpowiedź asystenta jest strumieniowana (SSE w odpowiedzi na `POST`) i zapisywana z `user_id` autora prośby. Oczekujące potwierdzenie zakończenia zakupów żyje w `chat_pending_actions` (klucz: `user_id`) i jest kasowane na początku następnej tury tego użytkownika. Model dostaje instrukcję systemową (zasady, login rozmówcy, lista JSON, preferencje, data) i ostatnie `chat_history_limit` = 20 wiadomości. Lista na żywo działa przez Postgres `LISTEN/NOTIFY` (kanał `kupto_list`) i strumień SSE `/api/list/events`, który wysyła tylko sygnał `list_changed` (treść klient pobiera osobno). Konto ma tylko login (3–50 znaków) i hasło; #77 zamieni login na e-mail. Pasek z #80 pokazuje tytuł czatu z `chatTitle(profile)` (nazwa gospodarstwa), a opcje czatu mają „Wyczyść historię czatu”.

Model działa na Groq (darmowy limit 200k tokenów dziennie); sama instrukcja systemowa z listą to kilka tysięcy tokenów na każde wywołanie, więc każda dodatkowa tura i każdy token historii ma znaczenie.

## Goals / Non-Goals

**Goals:**
- Jeden wspólny wątek gospodarstwa, w którym widać, kto i kiedy napisał, i który odświeża się u pozostałych na żywo.
- Asystent rozumie rozmowę grupy (kto pisze, do kogo odpowiada), a akcje i potwierdzenia zostają przy autorze prośby.
- Imię w każdym koncie, bez blokowania istniejących użytkowników na dłużej niż jeden formularz.
- Migracja bezpieczna na produkcji i odwracalna bez utraty danych.

**Non-Goals:**
- Logowanie e-mailem, weryfikacja adresu, reset hasła (#77).
- Imiona w liście zakupów, historii, przepisach i planie obiadów — przejdą na imię razem z #77 (wtedy login znika z UI).
- Kilka wątków / „historia czatów”, adresowanie asystenta, strumieniowanie cudzej odpowiedzi asystenta na żywo, wskaźnik „X pisze…”.

## Decisions

### D1. Wątek gospodarstwa = `chat_messages` gospodarstwa bez flagi `private`

Nie dokładamy tabeli wątków: wątek gospodarstwa to wiadomości z `household_id` gospodarstwa i `private = false`, w kolejności `(created_at, id)`. Nowy indeks `(household_id, created_at)` obsługuje ten odczyt (dotychczasowy `(user_id, created_at)` zostaje dla limitu wiadomości). `user_id` dalej oznacza autora wiadomości członka, a przy odpowiedzi asystenta — autora prośby, na którą odpowiada; to pozwala bez nowych kolumn liczyć limit i wrócić do prywatnych wątków przy cofnięciu migracji. Wiadomości zostają w gospodarstwie także po odejściu autora (historia grupy). Nowy domownik widzi dotychczasowy wątek gospodarstwa — jak w zwykłych czatach grupowych.

`GET /api/chat/messages` zwraca ostatnie 200 wiadomości (bez paginacji — wątek grupowy rośnie szybciej niż prywatny). Każda: `id`, `role`, `content`, `created_at`, `author` (`{id, name}` dla wiadomości członka, `null` dla asystenta) i `mine`.

### D2. Dotychczasowe prywatne historie — archiwum, nie wątek gospodarstwa

Rozważone: (a) przeniesienie do wątku gospodarstwa, (b) usunięcie, (c) archiwum. Wybrane (c): migracja dodaje `chat_messages.private BOOLEAN NOT NULL` i oznacza wszystkie istniejące wiadomości jako prywatne (`server_default` `true` przy dodaniu kolumny, potem `false` dla nowych wierszy). Archiwum nie jest widoczne w wątku gospodarstwa ani w kontekście modelu i nie ma UI.

- Przeciw (a): wiadomości pisano jako prywatne — ujawnienie ich domownikom bez zgody autora to zmiana umowy z użytkownikiem; do tego przeplecione po czasie rozmowy kilku osób z asystentem (każda ze swoimi „tak” i propozycjami) byłyby nieczytelne i myliłyby model.
- Przeciw (b): nieodwracalne; backup przed wdrożeniem pomaga tylko przy pełnym odtworzeniu bazy.
- (c) jest w pełni odwracalne: `downgrade` usuwa kolumnę i wszystkie wiadomości (także grupowe, zapisane z `user_id` autora prośby) wracają do prywatnych wątków, jak przed zmianą. Archiwum można później udostępnić autorowi albo usunąć osobną migracją.

### D3. Imię: `users.name`, wymagane przy rejestracji, uzupełniane po zalogowaniu

`users.name VARCHAR(40) NULL` — `NULL` tylko dla kont sprzed zmiany. `POST /api/auth/register` wymaga `name` (1–40 znaków po przycięciu spacji, nie same spacje); `PATCH /api/users/me` z `{name}` zmienia imię (ta sama walidacja) i zwraca profil; `GET /api/users/me` zwraca `name` (może być `null`). Imię nie jest unikalne — dwie „Anie” w gospodarstwie rozróżnia kolor własnych dymków, a w razie potrzeby same zmienią imię na „Ania K.”.

Istniejące konta: rozważono blokadę samego czatu albo całej aplikacji. Wybrano blokujący ekran po zalogowaniu (przed wyborem gospodarstwa) — jeden formularz, jedno miejsce w `App.tsx`, bez stanu „czat zablokowany, lista działa”. Backend nie odrzuca żądań kont bez imienia (zgodność ze starymi kartami PWA w cache); w czacie takie konto jest podpisywane loginem (D4).

### D4. Wyświetlana nazwa: imię, zapasowo login

Funkcja `display_name(user)` zwraca imię, a gdy go brak — login. Używają jej: autor wiadomości w czacie, kontekst modelu (historia, `requested_by` i `shopping_now` w liście JSON, „Ostatnią wiadomość napisał(a)…”) oraz powiadomienia push („Ala idzie na zakupy”, „Ala: zakupy zakończone”) — push widzą domownicy, dla których imię jest naturalniejsze niż login, a po #77 login byłby adresem e-mail. Pozostałe widoki (lista, historia, przepisy, plan obiadów, domownicy) zostają przy loginie; przejdą na `display_name` w #77.

### D5. Kontekst modelu: ostatnie 20 wiadomości z 24 h, z imionami autorów

- Historia: ostatnie `chat_history_limit` (20) nieprywatnych wiadomości wątku, najwyżej z ostatnich `chat_history_max_age_hours` (24) godzin — w grupie wątek rośnie szybciej, a rozmowa sprzed doby rzadko jest potrzebna, za to kosztuje tokeny w każdej turze. Bieżąca wiadomość jest zawsze ostatnia.
- Wiadomości członków mają przedrostek imienia: `{"role": "user", "content": "Ala: kup mleko"}`; odpowiedzi asystenta bez zmian (bez przedrostka, by model go nie naśladował). Bez godzin — kolejność wystarcza, a znacznik czasu w każdej wiadomości to kilkanaście tokenów więcej.
- Instrukcja: „Rozmawiasz z…” zastępuje „Piszesz w czacie grupowym gospodarstwa „X”. Ostatnią wiadomość napisał(a) Ala — odpowiadasz jej; zmiany na liście zapisują się jako jej.” oraz jedno zdanie zasady potwierdzeń (D6). Prompt rośnie o ok. 60 tokenów; zasady bez innych zmian.
- Ukrycie historii u siebie (D8) nie zmienia kontekstu modelu.

### D6. Potwierdzenia tylko od autora prośby

Rekomendacja z #78 przyjęta: potwierdzić może tylko osoba, która złożyła prośbę.

- Zakończenie zakupów: oczekująca akcja dalej jest w `chat_pending_actions` z kluczem `user_id` autora i jest kasowana na początku jego następnej tury. Wiadomości innych domowników jej nie widzą (instrukcja dostaje notatkę tylko w turze autora) i nie zużywają — „tak” od Oli nie zakończy zakupów Ali. Notatka mówi wprost, że prośba dotyczy rozmowy z tą osobą.
- Propozycje z rozmowy (zasady 4, 4a, 4e — produkty, składniki, plan obiadów) nie mają stanu po stronie serwera; o potwierdzeniu decyduje model na podstawie historii. Nowe zdanie w zasadach: potwierdzeniem propozycji jest tylko odpowiedź osoby, której ją złożono; gdy odpowiada ktoś inny, asystent traktuje to jak nową prośbę tej osoby. Weryfikacja: ewaluacja `-m llm` (scenariusz „tak” od innego domownika).

### D7. Asystent odpowiada na każdą wiadomość

Rozważono odpowiadanie tylko po zaadresowaniu („@Kupto”, „asystencie”). MVP: na każdą wiadomość — tak działa dzisiejszy czat, domownicy piszą głównie do asystenta (zgłaszanie potrzeb), a wykrywanie adresowania wymagałoby albo konwencji, której nikt nie zna, albo dodatkowego wywołania modelu (drożej niż odpowiedź). Koszt: rozmowa domowników między sobą („będę o 18”) też wywołuje model; zasada 1 każe wtedy krótko odpowiedzieć. Jeśli w logach `llm_usage` takie tury okażą się istotne, kolejnym krokiem jest przełącznik „asystent tylko na @Kupto” — bez zmiany modelu danych.

### D8. Ukrycie historii u siebie zamiast usuwania

W wątku grupowym usunięcie wiadomości przez jedną osobę kasowałoby rozmowę wszystkim. Rozważono: tylko właściciel może czyścić; usunięcie opcji; ukrycie u siebie. Wybrano ukrycie: `users.chat_hidden_before` (timestamptz) — `DELETE /api/chat/messages` ustawia go na teraz (i jak dotąd kasuje własną oczekującą akcję), a `GET` zwraca tylko nowsze wiadomości. Pozostali domownicy i model widzą wszystko dalej. Opcja w arkuszu: „Ukryj historię u siebie” z potwierdzeniem mówiącym, że domownicy nadal ją widzą. Znacznik jest per użytkownik, nie per gospodarstwo — po przejściu do innego gospodarstwa ukrywa też starsze wiadomości nowego wątku; to rzadki przypadek, akceptujemy.

### D9. Wiadomości na żywo przez istniejący strumień listy

Nie otwieramy drugiego strumienia (limit połączeń HTTP/1.1 na domenę, drugie połączenie LISTEN): kanał `kupto_list` dostaje rodzaj `chat`, a `/api/list/events` wysyła zdarzenie `chat_changed`. `Subscription` zbiera zbiór rodzajów sygnałów zamiast jednej flagi, więc `list_changed` i `chat_changed` nie zlewają się w jedno. Sygnał `chat` publikujemy w transakcji zapisu wiadomości członka i odpowiedzi asystenta (dostarczany po commicie, jak sygnały listy). Ukrycie historii nie publikuje sygnału (dotyczy jednej osoby; klient sam odświeża).

Klient: `ListEventsConnection` przekazuje `chat_changed` do słuchaczy czatu (`onChatChanged`), a przy ponownym połączeniu i powrocie karty odświeża także czat. `ChatView` na sygnał odświeża wątek; w trakcie własnej wymiany odkłada to do jej końca (i tak pobiera wtedy wątek), by lokalne dymki wymiany nie pojawiły się podwójnie. Odpowiedź asystenta na cudzą wiadomość pojawia się u pozostałych w całości po jej zapisaniu. Bez działającego strumienia (polling listy) czat odświeża się przy własnej wymianie i po ponownym połączeniu.

### D10. UI czatu

- Dymek członka: nad treścią imię autora (u innych) i godzina; własne po prawej w kolorze akcentu, cudze po lewej w neutralnym kolorze z obramowaniem; asystent po lewej, w kolorze asystenta, z etykietą „Asystent”. Godzina w strefie przeglądarki (`toLocaleTimeString("pl-PL", {hour, minute})`), dla wiadomości sprzed dzisiejszego dnia z datą („23.10, 18:05”).
- Szerokość: dymki `max-width: 85%`, `overflow-wrap: anywhere`, meta w jednym wierszu z `min-width: 0` i skracaniem imienia — bez przewijania w bok przy 375 px (`viewport.test.ts`).
- Nagłówek czatu: „Czat gospodarstwa” zamiast „Asystent”; podpowiedź przy pustym wątku mówi, że piszą wszyscy domownicy i asystent.
- `chatTitle(profile)` zostaje nazwą gospodarstwa — to jest nazwa czatu grupowego (gospodarstwo „Dom” = czat „Dom”); aktualizujemy tylko komentarz.

### D11. Migracja `0012`

Addytywna: `users.name` (NULL), `users.chat_hidden_before` (NULL), `chat_messages.private` (NOT NULL, istniejące = `true`, domyślnie `false`), indeks `ix_chat_messages_household_id_created_at`. Bez przenoszenia danych i bez długich blokad (dodanie kolumny z `server_default` stałej w Postgres 11+ nie przepisuje tabeli). `downgrade` usuwa kolumny i indeks — gubi imiona i znaczniki ukrycia, wiadomości wracają do prywatnych wątków. Test: `test_migrations.py` na danych z `SEED_STATEMENTS` (upgrade z 0011, sprawdzenie oznaczenia archiwum i domyślnych wartości nowych wierszy, downgrade, ponowny upgrade).

## Risks / Trade-offs

- [Więcej wywołań modelu w grupie — każda wiadomość domownika to tura] → limit 30 wiadomości/h na użytkownika bez zmian; logi `llm_usage` pokażą, czy potrzebny przełącznik z D7.
- [Model może uznać „tak” innego domownika za potwierdzenie propozycji] → zasada w prompcie i ewaluacja; zakończenie zakupów jest chronione stanem serwera niezależnie od modelu.
- [Równoległe wiadomości dwóch osób] → każda tura odpowiada swojemu autorowi i działa na jego koncie; odpowiedź zapisuje się po zakończeniu, więc w wątku może wylądować po cudzej wiadomości — model i UI rozróżniają adresata po kolejności i imieniu w instrukcji.
- [Archiwum prywatnych rozmów bez UI] → dane zostają (odwracalność); decyzja o udostępnieniu lub usunięciu w osobnym issue.
- [Konta bez imienia z otwartą starą wersją PWA] → backend akceptuje je dalej, a w czacie podpisuje loginem; nowa wersja frontu poprosi o imię.
- [Opcja „Ukryj historię u siebie” różni się od specyfikacji app-navigation z #80 („Wyczyść historię czatu”)] → zmiana `simple-nav` nie jest jeszcze zarchiwizowana; przy archiwizacji spec `app-navigation` trzeba zaktualizować o nową nazwę opcji.

## Migration Plan

1. Backup bazy (użytkownik, przed merge).
2. Wdrożenie: `alembic upgrade head` (0012) przy starcie, potem nowa wersja aplikacji. W krótkim oknie między migracją a startem nowej wersji stara wersja zapisuje wiadomości z `private = false` — trafią do wątku gospodarstwa; akceptowalne.
3. Rollback: poprzednia wersja aplikacji + `alembic downgrade 0011` (wiadomości wracają do prywatnych wątków, imiona giną).

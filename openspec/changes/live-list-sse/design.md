# Design

## Context

- Frontend pobiera listę `GET /api/list` pollingiem co 5 s (`frontend/src/api/queries.ts`). Odpowiedź jest per użytkownik: zawartość wspólna, ale kolejność grup i znacznik `pinned` wynikają z przypięć zalogowanego użytkownika.
- Wszystkie zmiany listy przechodzą przez `kupto/lists/service.py` (REST i narzędzia czatu), zmiany kolejności kategorii — przez `kupto/lists/category_order.py`. Każda operacja kończy się własnym `commit`.
- Produkcja: Caddy (`flush_interval -1`) → nginx (`/api/`: `proxy_buffering off`, `proxy_read_timeout 300s`) → jeden proces uvicorn. ADR 0001 wymaga, żeby rozgłaszanie działało także przy kilku instancjach backendu, więc stan w pamięci procesu nie wystarcza — kanałem jest Postgres `LISTEN/NOTIFY`.
- Pula SQLAlchemy ma domyślnie 5 + 10 połączeń; długie strumienie nie mogą jej trzymać.
- Bez migracji bazy (równolegle trwają prace z migracjami).

## Goals / Non-Goals

**Goals:**
- Sygnał o zmianie listy dociera do wszystkich otwartych klientów gospodarstwa w ułamku sekundy, niezależnie od tego, która instancja backendu obsłużyła zmianę.
- Strumień nie zużywa połączenia z puli bazy; jedno połączenie `LISTEN` na proces.
- Odporność: zerwanie połączenia `LISTEN`, pośredników lub sieci klienta kończy się ponownym połączeniem i pobraniem aktualnej listy, a do tego czasu działa polling co 30 s.

**Non-Goals:**
- Przesyłanie treści listy lub różnic w strumieniu, odtwarzanie pominiętych zdarzeń (`Last-Event-ID`).
- Strumień zmian dla czatu, gospodarstwa czy historii zakupów.
- Zmiany w service workerze (PWA) — on nie może cache'ować `/api/*`, w tym strumienia.

## Decisions

### D1. Strumień niesie sygnał „lista się zmieniła”, a klient pobiera listę zwykłym GET

Zdarzenie `list_changed` ma puste dane (`{}`); klient po nim unieważnia zapytanie listy i pobiera `GET /api/list`.

- Odpowiedź listy jest per użytkownik (kolejność kategorii), więc wysyłanie treści wymagałoby renderowania listy osobno dla każdego subskrybenta przy każdej zmianie — a w większości przypadków klient i tak by jej nie wyświetlił (np. karta czatu).
- Treść listy nie mieści się pewnie w limicie `NOTIFY` (8000 bajtów), więc i tak trzeba by ją czytać z bazy po stronie odbiorcy.
- Autoryzacja i kształt danych zostają w jednym miejscu (`GET /api/list`); strumień nie ujawnia niczego poza faktem zmiany.
- Koszt: jeden dodatkowy GET na zmianę na klienta — przy kilku domownikach pomijalny, a i tak dużo mniejszy niż polling co 5 s.

**Wersja w zdarzeniu — świadomie nie.** Monotoniczna wersja listy wymagałaby kolumny (migracja), a nie daje tu korzyści: pobranie listy jest idempotentne, kolejne sygnały są łączone (D5), a po każdym (ponownym) połączeniu klient i tak pobiera listę. Z tego samego powodu serwer nie nadaje `id:` i nie obsługuje `Last-Event-ID`. Alternatywa `txid` z Postgresa nie jest monotoniczna względem kolejności commitów, więc nie nadaje się na wersję.

### D2. `NOTIFY` w tej samej transakcji co zmiana

Serwis wywołuje `SELECT pg_notify('kupto_list', <json>)` tuż przed `commit`. Postgres dostarcza powiadomienia dopiero po zatwierdzeniu transakcji, a przy rollbacku je odrzuca — dostajemy semantykę „po commicie” bez osobnego haka i bez ryzyka sygnału o zmianie, która się nie utrwaliła. Identyczne powiadomienia w jednej transakcji Postgres łączy w jedno.

Alternatywy: hak SQLAlchemy `after_commit` + osobne połączenie do `NOTIFY` (dodatkowe połączenie, ryzyko utraty sygnału przy awarii między commitem a `NOTIFY`); bus w pamięci procesu (nie działa przy kilku instancjach).

### D3. Publikacja w warstwie serwisu

Wołają ją funkcje `service.add_needs`, `update_need`, `withdraw_need`, `remove_item`, `set_bought`, `finish_shopping` (tylko gdy coś przeniesiono), `category_order.pin/unpin/reset` oraz `households.remove_member/leave_household`. Narzędzia czatu korzystają z tych samych funkcji, więc publikują bez zmian w `chat/tools.py` i `chat/prompt.py`; nie ma ryzyka, że nowy endpoint lub narzędzie „zapomni” o zdarzeniu, o ile zmienia listę przez serwis.

### D4. Jeden kanał, mały ładunek z zakresem

Kanał `kupto_list`, ładunek JSON `{"household": int, "user": int | null, "kind": "changed" | "left"}`:
- `changed` bez `user` — zmiana wspólnej listy, trafia do wszystkich subskrybentów gospodarstwa.
- `changed` z `user` — zmiana kolejności kategorii użytkownika; trafia tylko do jego strumieni (np. drugi telefon), bo innym członkom lista się nie zmienia.
- `left` z `user` — użytkownik opuścił gospodarstwo lub został usunięty; broker zamyka jego strumienie w tym gospodarstwie (klient przy ponownym łączeniu dostaje 409).

Filtrowanie po `household` odbywa się w brokerze, więc subskrybent nigdy nie widzi sygnałów innego gospodarstwa.

### D5. Broker: jedno połączenie `LISTEN` na proces

`ListEventBroker` (w `app.state`) trzyma jedno surowe połączenie asyncpg (poza pulą SQLAlchemy) z `LISTEN kupto_list` i słownik `household_id → subskrypcje`.
- Start leniwy przy pierwszej subskrypcji (nie trzeba połączenia, gdy nikt nie słucha; testy nie muszą uruchamiać lifespan), zamknięcie w lifespan aplikacji.
- Subskrypcja nie ma kolejki — tylko flagę „zmieniono” (`asyncio.Event`) i flagę zamknięcia. Wolny klient dostaje jeden zbiorczy sygnał zamiast rosnącej kolejki.
- Utrata połączenia `LISTEN` (restart bazy, sieć): broker zamyka wszystkie subskrypcje — klienci łączą się ponownie i pobierają listę, więc nic nie ginie po cichu. Nowe subskrypcje czekają (do kilku sekund) na ponowne połączenie brokera; jeśli się nie uda, endpoint zwraca 503 i klient zostaje przy pollingu 30 s. Tym samym „otwarty strumień” zawsze oznacza „sygnały są dostarczane”.

### D6. Endpoint `GET /api/list/events`

- Zależności `CurrentUser`/`CurrentHousehold` jak w całym `/api/list` (401 bez sesji, 409 `no_household`).
- Przed zwróceniem `StreamingResponse` sesja bazy jest zamykana — połączenie wraca do puli, strumień trzyma tylko subskrypcję w brokerze.
- Format (SSE): na początku `retry: 3000` i `event: ready`, potem `event: list_changed` z `data: {}`, a w ciszy komentarz `: ping` co `LIST_EVENTS_HEARTBEAT_SECONDS` (domyślnie 20 s — poniżej 300 s nginx i typowych 30–60 s limitów bezczynności proxy/NAT na telefonach). Nagłówki `Cache-Control: no-cache` i `X-Accel-Buffering: no` jak w czacie.
- Sprzątanie: generator wyrejestrowuje subskrypcję w `finally` — także przy anulowaniu po rozłączeniu klienta.

### D7. Frontend: `EventSource` + polling jako fallback

- `EventSource` (ciasteczko sesji idzie samo, bo ten sam origin) zamiast fetch-stream: wbudowane ponowne łączenie po zerwaniu sieci i brak potrzeby własnych nagłówków. Gdy przeglądarka zamyka strumień na dobre (błąd HTTP, np. 503/409/401), klient od razu pobiera listę — 409 `no_household` przenosi wtedy do zakładania gospodarstwa, a 401 do logowania, tak jak przy zwykłych zapytaniach — i próbuje ponownie z wykładniczym opóźnieniem (3 s → 60 s).
- Stan „na żywo” = otrzymano `ready` i nie było błędu. Wtedy `useShoppingList` nie polluje; w przeciwnym razie polluje co 30 s.
- Każde `ready` po wcześniejszym połączeniu, każde `list_changed` i powrót karty (`visibilitychange`) unieważnia zapytanie listy. Karta w tle zamyka strumień (oszczędza baterię i połączenia), a po powrocie łączy się ponownie.
- Połączenie żyje tak długo jak komponent korzystający z `useShoppingList` (dziś jeden: `ListView`, zamontowany przez cały czas pracy z aplikacją, także na zakładce czatu) — bez zmian w `ListView.tsx`.

### D8. nginx i Caddy bez zmian

`/api/` w `frontend/nginx.conf` ma już `proxy_buffering off`, `proxy_cache off`, HTTP/1.1 i `proxy_read_timeout 300s`; Caddy ma `flush_interval -1`. Heartbeat 20 s utrzymuje połączenie w tych limitach, więc osobna lokacja dla `/api/list/events` nie jest potrzebna. Service worker PWA nie może przechwytywać `/api/*` (zwłaszcza strumienia).

## Risks / Trade-offs

- [Każdy otwarty klient trzyma długie połączenie HTTP przez Caddy i nginx] → skala to kilka gospodarstw; karta w tle zamyka strumień; domyślne limity połączeń nginx (`worker_connections 1024`) wystarczają z zapasem.
- [Utrata sygnału, gdy połączenie `LISTEN` padnie między commitem a dostarczeniem] → broker zamyka strumienie przy utracie połączenia; klienci po ponownym połączeniu pobierają listę; dodatkowo polling 30 s, gdy strumień nie działa.
- [Wyścig: zmiana między pobraniem listy a otwarciem strumienia] → po `ready` klient pobiera listę, jeśli wcześniej był już połączony; przy pierwszym połączeniu lista jest pobierana równolegle przez zwykłe zapytanie, a ewentualna zmiana w tej szczelinie (milisekundy) pokryje kolejny sygnał lub powrót do karty.
- [Zmiana listy poza serwisem (np. ręczny SQL, przyszły kod)] → nie wygeneruje sygnału; konwencja „zmiany tylko przez serwis” jest już zapisana w docstringu modułu.
- [Usunięcie gospodarstwa kaskadowo przy wyjściu ostatniego członka] → zdarzenie `left` zamyka jego strumień; innych subskrybentów nie ma.

## Migration Plan

Wdrożenie zwykłą aktualizacją obrazów. Stare klienty (polling 5 s) działają dalej do przeładowania strony. Wycofanie: powrót do poprzednich obrazów — endpoint znika, a nowy frontend przechodzi na polling 30 s (strumień zwraca błąd), więc nawet mieszana wersja działa.

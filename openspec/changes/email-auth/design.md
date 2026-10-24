# Design

## Context

Konto ma login (3–50 znaków, unikalny), hasło (argon2 przez `pwdlib`) i od #78 imię. Sesja to JWT HS256 w ciasteczku httpOnly (`kupto_session`, 30 dni) z `sub` = id użytkownika; `get_current_user` przy każdym żądaniu wczytuje użytkownika z bazy, a `get_current_household` sprawdza przynależność — przez tę zależność przechodzą wszystkie funkcje gospodarstwa (lista, czat, historia, przepisy, plan, preferencje, push). Login jest pokazywany domownikom w liście, historii, przepisach, planie obiadów, preferencjach i na stronie gospodarstwa; właściciel dodaje domownika po loginie.

Produkcja: jedna instancja EC2 (eu-north-1) z Docker Compose, Caddy → nginx (`web`) → uvicorn z `--proxy-headers`. Sekrety z SSM `/kupto/*` trafiają do `/opt/kupto/.env`. Instancja ma rolę IAM `kupto-app`, IMDSv2 z `http_put_response_hop_limit = 1`. DNS domeny `bakweb.pl` jest w SEOHOST (poza AWS), rekord A `kupto.bakweb.pl` wskazuje Elastic IP.

## Goals / Non-Goals

**Goals:**
- Rejestracja i logowanie e-mailem, weryfikacja adresu, odzyskanie hasła bez zdradzania, czy konto istnieje.
- Istniejące konta działają bez przerwy i przechodzą na e-mail przy najbliższym logowaniu.
- Merge przed konfiguracją SES nie psuje produkcji.
- Domownicy widzą imiona, nie loginy ani adresy.

**Non-Goals:**
- Zmiana potwierdzonego adresu, usunięcie konta, „wyloguj wszędzie” (#54), limit prób logowania, 2FA, logowanie przez Google itp., zaproszenia do gospodarstwa linkiem.

## Decisions

### D1. Model danych (migracja `0013`)

- `users.email VARCHAR(254) NULL` — zapisywany po `strip()` i `lower()`; unikalny indeks `uq_users_email_lower` na `lower(email)` (unikalność bez względu na wielkość liter także przy zapisie z pominięciem aplikacji). `NULL` = konto sprzed zmiany, które jeszcze nie potwierdziło adresu.
- `users.email_verified_at TIMESTAMPTZ NULL` — potwierdzenie adresu.
- `users.verify_email_by TIMESTAMPTZ NULL` — termin potwierdzenia (D3).
- `users.sessions_valid_after TIMESTAMPTZ NULL` — sesje wydane wcześniej są nieważne (D6).
- `users.login` przestaje być wymagany (nowe konta go nie mają); unikalność bez zmian.
- `auth_tokens`: `id`, `user_id` (FK, `ON DELETE CASCADE`), `purpose` (`verify_email` | `reset_password`, tekst bez enuma), `token_hash CHAR(64)` unikalny (SHA-256 hex), `email` (adres, na który wysłano link), `created_at`, `expires_at`, `used_at`.
- `auth_rate_events`: `id`, `action`, `key_hash CHAR(64)`, `created_at`, indeks `(action, key_hash, created_at)` (D5).

Adres e-mail jest zapisywany małymi literami w całości (także część lokalna) — w praktyce dostawcy poczty ignorują wielkość liter, a jedna postać upraszcza porównania. Walidacja w aplikacji: najwyżej 254 znaki, jedna `@`, część lokalna ≤ 64 znaki bez spacji, domena z kropką i etykietami `[a-z0-9-]` (także IDN po zamianie przez przeglądarkę na punycode). Bez sprawdzania MX — prawdziwą walidacją jest link weryfikacyjny.

Pola zapisywane przy rejestracji i weryfikacji są addytywne, więc migracja nie dotyka istniejących wierszy poza zdjęciem `NOT NULL` z loginu.

### D2. Tokeny jednorazowe

Token = `secrets.token_urlsafe(32)` (256 bitów); w bazie tylko `sha256(token)` — wyciek bazy nie daje działających linków. Ważność: weryfikacja 48 h (`EMAIL_VERIFICATION_TTL_HOURS`), reset hasła 30 min (`PASSWORD_RESET_TTL_MINUTES`). Wystawienie nowego tokenu danego rodzaju usuwa niewykorzystane tokeny tego rodzaju dla konta (ważny jest tylko najnowszy link). Zużycie jest atomowe: `UPDATE auth_tokens SET used_at = now() WHERE token_hash = … AND purpose = … AND used_at IS NULL AND expires_at > now() RETURNING …` — dwa równoległe kliknięcia nie użyją tokenu dwa razy. Nieprawidłowy, wygasły i użyty token dają ten sam błąd 400 `invalid_token` („Link jest nieprawidłowy, wygasł albo został już użyty.”).

Linki: `https://<KUPTO_DOMAIN>/verify-email#token=…` i `…/reset-password#token=…`. Token jest we fragmencie adresu — przeglądarka nie wysyła go do serwera, więc nie trafia do logów Caddy/nginx ani do nagłówka `Referer`; strona frontu odczytuje go i wysyła w treści `POST`. Bez `KUPTO_DOMAIN` (dev) linki prowadzą do `http://localhost:5173` (Vite). Wpisy z tabeli nie są sprzątane osobno — konto ma co najwyżej po jednym niewykorzystanym tokenie każdego rodzaju, a zużyte/wygasłe usuwa kolejne wystawienie.

### D3. Konto niezweryfikowane: 7 dni z banerem, potem blokada

Rozważone: (a) brak logowania do czasu weryfikacji, (b) pełny dostęp z banerem bez terminu, (c) dostęp z banerem i terminem. Wybrane (c): nowe konto od razu działa (można założyć gospodarstwo i dodać pierwsze produkty), a `verify_email_by = pierwszy faktycznie wysłany link + 7 dni` (`EMAIL_VERIFICATION_GRACE_DAYS`). Przy niedostępnej wysyłce (D8) link nie wychodzi i termin nie jest ustawiany — konto bez terminu nigdy nie jest blokowane, a gdy wysyłka zacznie działać, widzi baner „Potwierdź adres — wyślemy na niego link” i dostaje 7 dni od wysłania. Do terminu aplikacja pokazuje baner „Potwierdź adres e-mail” z przyciskiem ponownego wysłania i zmiany adresu. Po terminie:

- backend: `get_current_household` zwraca 403 z kodem `email_unverified` — zablokowane są wszystkie funkcje gospodarstwa (lista, czat, historia, przepisy, plan, push, strumień zmian). Profil, zmiana imienia, podanie/zmiana adresu, wylogowanie działają;
- frontend: blokujący ekran „Potwierdź adres e-mail” (adres, „Wyślij link ponownie”, „Zmień adres”, „Wyloguj”).

(a) odpada, bo opóźniony lub zaspamowany mail blokowałby pierwsze użycie, a przy niedostępnej wysyłce (D8) nikt nie mógłby się zarejestrować. (b) pozwalałby trwale zająć cudzy adres. Termin liczy się od pierwszego wysłanego linku (przy rejestracji albo przy pierwszym podaniu adresu w starym koncie, D4) i nie jest przesuwany przy ponownym wysłaniu. Blokada działa tylko, gdy wysyłka jest dostępna (D8).

Zmiana adresu przed potwierdzeniem (`POST /api/users/me/email` z innym adresem) wysyła link na nowy adres; `users.email` zmienia się dopiero po kliknięciu (do tego czasu logowanie dotychczasowym adresem). Zmiana już potwierdzonego adresu jest poza zakresem (powinna wymagać hasła) — endpoint zwraca 409.

### D4. Konta sprzed zmiany (login bez e-maila)

- Logowanie loginem działa, dopóki konto nie ma adresu w `users.email`, czyli do potwierdzenia adresu. Adres podany, ale niepotwierdzony, żyje tylko w tokenie (`auth_tokens.email`) — nie zajmuje adresu w `users` i nie da się nim logować. Po potwierdzeniu `users.email` = adres, `email_verified_at` = teraz, a od tej chwili konto loguje się tylko e-mailem (login nie zostaje alternatywą: issue zastępuje login adresem, login był pokazywany domownikom i nie ma sensu utrzymywać dwóch identyfikatorów; mail weryfikacyjny i strona potwierdzenia mówią to wprost). Kolumna `login` zostaje w bazie (cofnięcie migracji, diagnostyka).
- Po zalogowaniu, gdy wysyłka jest dostępna: blokujący ekran „Podaj adres e-mail” (jak „Jak masz na imię?” z #78; kolejność: imię, adres, gospodarstwo). Po podaniu adresu ustawiany jest `verify_email_by` i dalej jak w D3 — 7 dni z banerem, potem blokada. Zwykły ekran zamiast natychmiastowej blokady do weryfikacji: domownik w trakcie zakupów nie traci listy, bo mail doszedł z opóźnieniem.
- Backend blokuje gospodarstwo także kontu bez podanego adresu (403 `email_required`), gdy wysyłka działa — stare karty PWA bez ekranu dostaną błąd z czytelnym komunikatem zamiast cichego obejścia.
- Gdy wysyłka jest niedostępna: brak ekranu i blokady; na profilu informacja, że wysyłka maili jest jeszcze niedostępna.

Wyszukiwanie konta przy logowaniu: `lower(email) = :id` albo `login = :id AND email IS NULL` (preferowane trafienie po adresie). Ten sam helper służy do dodawania domownika (D9).

### D5. Limity prób

Tabela `auth_rate_events` zamiast pamięci procesu: przeżywa restart i wdrożenie, działa przy wielu workerach. Klucz to `sha256(akcja + wartość)` — w bazie nie ma adresów ani IP otwartym tekstem. Zdarzenie zapisywane i zatwierdzane przed właściwą akcją (także gdy konto nie istnieje — inaczej limit zdradzałby istnienie konta). Sprawdzenie i zapis są atomowe: w tej samej transakcji, przed liczeniem, `pg_advisory_xact_lock` na 64 bitach skrótu każdego klucza (w stałej kolejności — bez zakleszczeń) szereguje równoległe żądania z tym samym kluczem do zatwierdzenia, więc seria równoległych prób nie przekroczy limitu. Zdarzenia starsze niż doba usuwa średnio co setny zapis (losowo; indeks na `created_at`) — nie każde żądanie; starsze zdarzenia i tak nie są liczone.

| Akcja | Klucz | Limit |
|---|---|---|
| rejestracja | IP | 5 / h |
| prośba o reset hasła | adres | 3 / h |
| prośba o reset hasła | IP | 10 / h |
| wysłanie linku weryfikacyjnego (podanie adresu, ponowne wysłanie) | konto | 5 / h |
| wysłanie linku weryfikacyjnego | adres | 3 / h |

Przekroczenie: 429 z `Retry-After` (czas do wygaśnięcia najstarszego zdarzenia w oknie). IP to `request.client.host` po `--proxy-headers`: Caddy nie ufa nadesłanemu `X-Forwarded-For` (bez `trusted_proxies` zastępuje go adresem klienta), nginx dopisuje adres Caddy, a uvicorn z `--forwarded-allow-ips='*'` bierze pierwszy adres listy — czyli prawdziwego klienta. Rejestracja wysyła mail weryfikacyjny bez osobnego limitu (limit rejestracji go obejmuje). Limitu logowania nie dodajemy (poza zakresem; argon2 i tak spowalnia zgadywanie).

### D6. Reset hasła

- `POST /api/auth/password-reset {email}` → zawsze 202 „Jeśli konto z tym adresem istnieje, wysłaliśmy na nie link…”. Link dostaje konto z `users.email` = adres (potwierdzony albo nie — dla nowego konta adres jest jedynym identyfikatorem, a link i tak trafia do właściciela skrzynki). Konto sprzed zmiany z adresem tylko w tokenie (D4) nie dostaje linku — inaczej literówka w adresie oddawałaby konto właścicielowi tej skrzynki.
- Mail wysyłany jest w tle (`BackgroundTasks`, po wysłaniu odpowiedzi), więc czas odpowiedzi nie zależy od istnienia konta ani od SES; błąd wysyłki trafia tylko do logu.
- `POST /api/auth/password-reset/confirm {token, password}` → nowe hasło (≥ 8 znaków), token zużyty, pozostałe tokeny resetu konta usunięte, adres potwierdzony (kliknięcie linku dowodzi dostępu do skrzynki; usuwa też ryzyko zajęcia cudzego adresu niepotwierdzoną rejestracją — prawowity właściciel przejmuje takie konto resetem), `sessions_valid_after = now()`. Bez automatycznego logowania — użytkownik loguje się nowym hasłem.
- Unieważnienie sesji: `get_current_user` odrzuca JWT z `iat` (sekundy) mniejszym niż `floor(sessions_valid_after)`. Reset zwykle wynika z podejrzenia, że ktoś zna hasło, więc stare sesje (np. na zgubionym telefonie) powinny wygasnąć; kosztuje to jedną kolumnę i porównanie w zależności, która i tak czyta użytkownika z bazy. Ogólne „wyloguj wszędzie” (#54) może użyć tej samej kolumny. Sesja wydana w tej samej sekundzie co reset przeżywa — akceptowalne.

### D7. Wysyłka maili: `MailSender`, SES przez API v2 (boto3)

`kupto.mail` definiuje `MailSender` (`async send(message)`, `delivers: bool`) i dwie implementacje:

- `LogMailSender` (`MAIL_BACKEND=log`, domyślny): nic nie wysyła. Loguje na INFO tylko zdarzenie `mail_not_sent` z tematem (bez adresu i treści). Z `MAIL_LOG_LINKS=true` (wyłącznie dev) loguje też adresata i treść z linkiem — wtedy `delivers = true`, bo deweloper „odbiera” link z logu. Produkcja nie ustawia `MAIL_LOG_LINKS`, więc tokeny nie trafiają do logów.
- `SesMailSender` (`MAIL_BACKEND=ses`): `boto3.client("sesv2", region_name=MAIL_SES_REGION).send_email(...)` w `asyncio.to_thread`, treść tekstowa (bez HTML — prostsze, mniej podejrzane dla filtrów). Poświadczenia z łańcucha boto3, czyli na EC2 z profilu instancji (IMDSv2).

SES przez HTTPS API zamiast SMTP: SMTP wymagałby użytkownika IAM z kluczem dostępu i pochodnym hasłem SMTP w SSM (długowieczny sekret do rotacji), a API v2 używa krótkotrwałych poświadczeń roli instancji i uprawnienia `ses:SendEmail` ograniczonego do tożsamości domeny. Koszt: zależność `boto3` (~15 MB w obrazie).

Kontener backendu łączy się z IMDS przez most Dockera, czyli o jeden skok dalej niż host — przy `http_put_response_hop_limit = 1` odpowiedź IMDSv2 nie dociera i boto3 nie dostaje poświadczeń. Dlatego `infra/main.tf` ustawia limit 2 (zalecany przez AWS dla kontenerów; zmiana w miejscu, bez restartu instancji).

**Ryzyko:** przy limicie 2 każdy kontener na serwerze (także `web`, `caddy`, `db`) mógłby pobrać poświadczenia roli instancji (zrzuty w S3, sekrety SSM `/kupto/*`, SES) — np. po przejęciu Caddy lub nginx. **Ograniczenie:** kontenery są w sieci `app` ze stałą podsiecią `172.30.0.0/24`, backend ma stały adres `172.30.0.10`, a `kupto-update.sh` (co 5 min, jako root, idempotentnie) dodaje w łańcuchu `DOCKER-USER` regułę `RETURN` dla backendu i `DROP` dla pozostałego ruchu z kontenerów do `169.254.169.254`. Procesów hosta (AWS CLI w skryptach) to nie dotyczy — ich ruch nie przechodzi przez `FORWARD`. Podszycie się pod adres backendu nie wystarczy: IMDSv2 wymaga pełnego połączenia TCP (odpowiedź trafiłaby do backendu). Pozostałe luki: po restarcie serwera reguły wracają przy pierwszym ticku timera (`OnBootSec=1min`); IMDS po IPv6 jest wyłączone (domyślne `http_protocol_ipv6`). Rozważone alternatywy: osobny proces-pośrednik do SES na hoście (więcej ruchomych części), klucz IAM użytkownika w SSM (długowieczny sekret), `network_mode: host` dla backendu (traci izolację sieci Compose).

Niepoprawna konfiguracja (`ses` bez `MAIL_FROM`) nie zatrzymuje aplikacji: błąd w logu i zachowanie jak `log` — wzorem kluczy VAPID.

### D8. Wysyłka niedostępna (produkcja przed konfiguracją SES)

`mail_enabled = sender.delivers`. Gdy `false` (domyślnie na produkcji po merge):

- rejestracja e-mailem działa, konto jest niezweryfikowane, ale nikt nie jest blokowany (ani nowe, ani stare konta) i nie ma banera ani ekranu „Podaj adres e-mail”;
- `POST /api/auth/password-reset` i `POST /api/users/me/email` zwracają 503 `mail_unavailable` („Wysyłka e-maili jest chwilowo niedostępna.”) — dla wszystkich adresów jednakowo, więc nic nie zdradzają; strona „Zapomniałem hasła” pokazuje komunikat od razu (`GET /api/auth/config` → `{mail_enabled}`);
- logowanie loginem i e-mailem działa jak dotąd.

Po włączeniu SES konta zarejestrowane w tym okresie mają termin weryfikacji już za sobą — zobaczą ekran blokady z „Wyślij link ponownie”, co zajmuje minutę. Stare konta zobaczą ekran „Podaj adres e-mail”.

### D8a. Rejestracja zdradza, że adres ma konto (świadomy kompromis)

`POST /api/auth/register` z zajętym adresem zwraca 409 „Konto z tym adresem e-mail już istnieje.” — w przeciwieństwie do resetu hasła (D6) ujawnia to istnienie konta. Zostawiamy, bo alternatywa (zawsze 201 i mail „masz już konto” na podany adres) myli użytkownika, który pomylił formularz, a do tego nie działa przy niedostępnej wysyłce (D8). Ryzyko ogranicza limit 5 rejestracji na godzinę z IP (D5) — odpytanie listy adresów jest powolne; aplikacja nie przechowuje danych, dla których samo istnienie konta byłoby wrażliwe.

### D9. Imiona zamiast loginów, dodawanie domownika

- `display_name(user)` = imię, zapasowo login (konta sprzed #78 bez imienia), a w ostateczności „Domownik”. Wszystkie odpowiedzi API pokazujące innego użytkownika używają `display_name`: zapotrzebowania i „kupione przez” w liście, „robi zakupy”, historia, autor przepisu, plan obiadów, preferencje, domownicy. Pola `login` w zapotrzebowaniach (`needs[].login`), kupujących (`shoppers[].login`), historii (`needs[].login`) i członkach (`members[].login`) zmieniają nazwę na `name` — zostawienie nazwy `login` z imieniem w środku myliłoby. Login i adres widzi tylko właściciel konta w profilu.
- Dodawanie domownika: `POST /api/households/me/members {email}` (stare pole `login` przyjmowane jako alias). Szukane jest konto z tym adresem — potwierdzonym, gdy wysyłka działa (inaczej ktoś mógłby zarejestrować cudzy adres i zostać dodany zamiast właściciela adresu); przy niedostępnej wysyłce także niepotwierdzonym — oraz, dla kont bez adresu, po loginie. 404: „Nie znaleziono konta o tym adresie e-mail.” Ujawnienie istnienia konta właścicielowi gospodarstwa jest jak dotąd (po loginie) — bez tego nie da się dodać domownika.
- Ekran „Nie należysz do gospodarstwa” podaje adres e-mail użytkownika do przekazania właścicielowi (i informację, że adres trzeba najpierw potwierdzić, gdy wysyłka działa), a dla konta bez adresu — login.

### D10. API

| Endpoint | Zmiana |
|---|---|
| `POST /api/auth/register` | `{email, password, name}` → 201; 409 przy zajętym adresie; mail weryfikacyjny w tle |
| `POST /api/auth/login` | `{email, password}` (alias `login`) → ciasteczko; 401 jednakowe dla wszystkich błędów |
| `GET /api/auth/config` | `{mail_enabled}` — publiczne, dla stron logowania i resetu |
| `POST /api/auth/verify-email` | `{token}` → 200 `{message}`; 400 `invalid_token`; 409, gdy adres zajęło w międzyczasie inne konto |
| `POST /api/auth/password-reset` | `{email}` → 202; 429; 503 `mail_unavailable` |
| `POST /api/auth/password-reset/confirm` | `{token, password}` → 200; 400 `invalid_token`; 422 |
| `POST /api/users/me/email` | `{email}` → profil; wysyła link na adres (także ponownie na ten sam); 409, gdy adres zajęty lub już potwierdzony; 429; 503 |
| `GET /api/users/me` | + `email` (potwierdzony, a jeśli brak — oczekujący na potwierdzenie), `email_verified`, `email_status` (`verified` / `unverified` / `missing`), `verify_email_by`, `email_blocked` (czy aplikacja jest zablokowana), `mail_enabled`; `login` może być `null` |

Endpointy weryfikacji i resetu nie wymagają sesji (link otwierany na innym urządzeniu niż aplikacja).

## Risks / Trade-offs

- [Mail w spamie / opóźniony] → 7 dni na potwierdzenie, ponowne wysłanie z UI; DKIM + SPF (MAIL FROM) + DMARC w DNS.
- [SES sandbox: wysyłka tylko na zweryfikowane adresy, 200 maili/dobę] → do czasu przyznania production access zostaw `MAIL_BACKEND=log` albo testuj na adresach zweryfikowanych w SES; kroki w `infra/README.md`.
- [Zajęcie cudzego adresu niepotwierdzoną rejestracją] → po włączeniu wysyłki takie konto po 7 dniach jest zablokowane, nie da się go dodać do gospodarstwa (D9), a właściciel adresu przejmuje je resetem hasła (D6).
- [Literówka w adresie starego konta] → adres nie jest zapisywany do potwierdzenia; reset hasła nie działa na adres z tokenu (D6).
- [Stare karty PWA wysyłają `login`] → aliasy pól w logowaniu i dodawaniu domownika; formularz rejestracji starej wersji dostanie 422 do czasu aktualizacji service workera.
- [IMDS hop limit 2: kontenery mogą pobrać poświadczenia roli] → reguła `DOCKER-USER` przepuszcza do IMDS tylko stały adres backendu (D7); rola ma wąskie uprawnienia.
- [Rejestracja ujawnia istnienie konta (409)] → świadomy kompromis UX (D8a), limit rejestracji na IP.
- [Logi z linkami] → tylko przy jawnym `MAIL_LOG_LINKS=true`; test sprawdza, że domyślnie log nie zawiera tokenu.

## Migration Plan

1. Backup bazy (właściciel, przed merge).
2. Merge: przy starcie `alembic upgrade head` (0013). Produkcja ma `MAIL_BACKEND` nieustawiony (`log`) → nic się nie blokuje, logowanie loginem działa, nowe konta rejestrują się e-mailem.
3. Właściciel: `terraform apply`, rekordy DNS w SEOHOST, wniosek o production access w SES, parametry SSM `MAIL_BACKEND=ses`, `MAIL_FROM` — od najbliższego ticku `kupto-update` wysyłka działa, stare konta dostają ekran „Podaj adres e-mail”.
4. Rollback: poprzednia wersja + `alembic downgrade 0012` — usuwa adresy, tokeny i limity; kontom bez loginu (zarejestrowanym e-mailem) nadaje login `<adres obcięty do 40 znaków>#<id>`, żeby przywrócić `NOT NULL`.

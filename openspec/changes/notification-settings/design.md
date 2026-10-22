# Design

## Context

Motywacja: `proposal.md`. Wymagania: `specs/notifications/spec.md`.

Stan obecny, który wpływa na podejście:

- `Notifier.deliver_to_users` (change `web-push`) przed wyborem subskrypcji przepuszcza adresatów przez `allowed_recipients(session, user_ids, notification_type)` — punkt zaczepienia zostawiony dla #32, dziś przepuszcza wszystkich. `deliver_to_household` wyznacza członków i woła `deliver_to_users`, więc jeden filtr obejmuje obie ścieżki.
- `NotificationType` to `StrEnum` o stabilnych wartościach (`shopping_started`, `items_added`, `shopping_finished`) — zapowiedzianych jako zapisywane w ustawieniach.
- Karta „Powiadomienia” (`notifications/NotificationSettings.tsx`) na stronie gospodarstwa pokazuje stan i przycisk włączania na tym urządzeniu; to jedyna strona ustawień.
- Przyszłość: #40 doda przypomnienia o zwykłych produktach — nowy typ powiadomienia, który być może powinien być domyślnie wyłączony.

## Goals / Non-Goals

**Goals:**

- Włączanie i wyłączanie każdego typu osobno, per użytkownik, respektowane przy każdej wysyłce.
- Bez zmian dla obecnych użytkowników (domyślnie wszystko włączone) i bez migracji danych.
- Dodanie nowego typu (#40) bez migracji, także z domyślnie wyłączoną wartością.

**Non-Goals:**

- Ustawienia per urządzenie (np. „na laptopie tylko zakończenie zakupów”).
- Godziny ciszy, częstotliwość, kanały inne niż Web Push.
- Typ przypomnień (#40) — dodaje go #40 razem z funkcją, żeby nie pokazywać przełącznika czegoś, co nie istnieje.

## Decisions

### D1. Ustawienia per użytkownik, nie per urządzenie

Issue mówi o ustawieniach per użytkownik. Wybór dotyczy treści („o czym chcę wiedzieć”), a nie urządzenia; włączenie powiadomień na urządzeniu pozostaje osobną, istniejącą decyzją (subskrypcja). Dzięki temu zmiana na telefonie obowiązuje też na laptopie, a filtr działa na poziomie adresatów, przed wyborem subskrypcji.

### D2. Model danych: jawne wybory, wartość domyślna w kodzie

Nowa tabela `notification_preferences`:

| Kolumna | Typ | Uwagi |
|---|---|---|
| `user_id` | FK `users.id`, `ON DELETE CASCADE` | część PK |
| `type` | `varchar(40)` | część PK — wartość `NotificationType` |
| `enabled` | `boolean NOT NULL` | wybór użytkownika |
| `updated_at` | `timestamp NOT NULL` | diagnostyka |

Wiersz istnieje tylko wtedy, gdy użytkownik coś zmienił; brak wiersza oznacza wartość domyślną typu z `DEFAULT_ENABLED` w `kupto.push.preferences` (dziś `True` dla wszystkich). Zapis to `INSERT … ON CONFLICT DO UPDATE`.

Dlaczego `varchar`, a nie typ enum Postgresa: dodanie wartości do enuma wymaga migracji (`ALTER TYPE … ADD VALUE`), a usunięcie — przebudowy typu. Poprawność typu sprawdza API (`NotificationType` w ścieżce → 422 dla nieznanego), a odczyt ignoruje wiersze z typami, których kod już nie zna.

Dlaczego jawne `enabled` zamiast samej listy wyciszonych typów: przy samych wyciszeniach typ domyślnie wyłączony (np. przypomnienia #40) wymagałby drugiej tabeli albo migracji. Z kolumną `enabled` nowy typ to jedna wartość w enumie i jeden wpis w `DEFAULT_ENABLED`; zmiana wartości domyślnej obejmuje wszystkich, którzy nie wybrali sami.

Alternatywy odrzucone: kolumny boolowskie w `users` (migracja dla każdego typu), kolumna JSON (trudniejszy filtr adresatów w SQL i walidacja).

### D3. Filtr adresatów w `allowed_recipients`

`allowed_recipients(session, user_ids, type)` deleguje do `preferences.recipients_wanting(...)`: jednym zapytaniem pobiera wiersze `(user_id, enabled)` dla adresatów i typu, a adresat przechodzi, gdy jego wiersz ma `enabled`, albo — bez wiersza — gdy typ jest domyślnie włączony. Filtr działa w zadaniu w tle, w chwili wysyłki, więc zmiana ustawień obowiązuje od następnego powiadomienia. Wołający (`lists/notifications.py`, czat) nic nie wiedzą o ustawieniach.

### D4. API

- `GET /api/push/preferences` → `{"types": [{"type": "shopping_started", "enabled": true}, …]}` — wszystkie znane typy w stałej kolejności (kolejność enuma), z wartościami domyślnymi tam, gdzie brak wyboru.
- `PUT /api/push/preferences/{type}` z `{"enabled": bool}` → ta sama odpowiedź co `GET` (stan po zmianie). Idempotentne; nieznany typ → 422.

Oba wymagają zalogowania, ale **nie** wymagają kluczy VAPID ani gospodarstwa: to zwykłe dane użytkownika, a przy wyłączonych powiadomieniach i tak nic nie jest wysyłane. Endpointy są w `push/router.py` (prefiks `/api/push`), obok subskrypcji.

### D5. Frontend

Przełączniki są częścią karty „Powiadomienia” jako `fieldset` „Powiadamiaj mnie, gdy…” z polami wyboru i krótkim opisem typu. Pokazywane, gdy serwer potwierdził dostępność powiadomień i przeglądarka je obsługuje (stany „włączone” i „wyłączone”) — w pozostałych stanach na tym urządzeniu i tak nie da się ich dostać, a ustawienia można zmienić na urządzeniu, na którym działają. Etykiety i opisy typów są w kodzie frontendu; typ nieznany frontendowi (nowszy backend) jest pomijany.

Zapis: `useMutation` z aktualizacją optymistyczną (`setQueryData`), wycofaniem przy błędzie i komunikatem; odpowiedź serwera zastępuje stan.

## Risks / Trade-offs

- [Wiersze z typem usuniętym z kodu zostają w bazie] → ignorowane przy odczycie; można je posprzątać przy usuwaniu typu.
- [Wszystkie typy wyłączone przy włączonej subskrypcji] → urządzenie nie dostaje nic, choć karta pokazuje „włączone” — przełączniki są tuż pod stanem urządzenia, więc widać przyczynę; akceptowalne.
- [Dodatkowe zapytanie przy każdej wysyłce] → jedno małe zapytanie po kluczu głównym w tej samej sesji co odczyt subskrypcji; pomijalne.

## Migration Plan

Migracja `0007` (`down_revision = "0006"`) tylko tworzy pustą tabelę — wdrożenie bez przestoju, stara wersja aplikacji jej nie używa. Downgrade usuwa tabelę: użytkownicy wracają do wartości domyślnych (wszystko włączone).

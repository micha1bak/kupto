# Proposal

## Why

Zapowiedziane powiadomienia o zakupach — „X idzie na zakupy” (#29), „Dopisano w trakcie” (#30), „Zakupy zakończone” z brakami (#31) — oraz ich ustawienia per użytkownik (#32) potrzebują wspólnej infrastruktury Web Push (#27): kluczy serwera, zapisanych subskrypcji urządzeń, wysyłki i obsługi powiadomień w service workerze. Bez niej każde z tych zadań musiałoby budować ją od nowa.

## What Changes

- Klucze VAPID z konfiguracji (`VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT`) — opcjonalne: bez nich (albo z błędnymi) backend działa, a powiadomienia są wyłączone. Polecenie do wygenerowania kluczy i instrukcja wpisania ich do SSM.
- Subskrypcje push urządzeń użytkownika: nowa tabela `push_subscriptions` (migracja Alembic `0005`, wyłącznie addytywna), kilka urządzeń na użytkownika, jedno urządzenie (endpoint) przypisane do jednego użytkownika.
- API: `GET /api/push/public-key` (404 `push_disabled`, gdy wyłączone), `PUT /api/push/subscriptions` (zapis/aktualizacja po endpoincie), `DELETE /api/push/subscriptions` (usunięcie); wszystkie wymagają zalogowania.
- Wysyłka poza obsługą żądania HTTP (zadanie w tle po commicie) z TTL, pilnością, limitem czasu i usuwaniem wygasłych subskrypcji (odpowiedź 404/410 usługi push). API wysyłki dla kolejnych zadań: `send_to_users` / `send_to_household` z typem powiadomienia.
- Service worker: wyświetlanie powiadomienia (tytuł, treść, tag do grupowania) i obsługa kliknięcia (fokus otwartej karty albo otwarcie adresu z powiadomienia).
- Frontend: sekcja „Powiadomienia” z przyciskiem „Włącz powiadomienia” (zgoda przeglądarki dopiero po kliknięciu) i stanami: włączone, wyłączone, zablokowane, nieobsługiwane, iPhone bez instalacji (informacja o dodaniu do ekranu początkowego), niedostępne na serwerze. Wylogowanie wyłącza powiadomienia na urządzeniu.
- Poza zakresem: konkretne powiadomienia #29–#31 i ustawienia typów #32.

## Capabilities

### New Capabilities

- `notifications`: powiadomienia push na urządzenia członków gospodarstwa — włączanie i wyłączanie na urządzeniu, subskrypcje, dostarczanie i wygląd powiadomień, działanie bez konfiguracji kluczy.

### Modified Capabilities

(brak)

## Impact

- **Backend**: pakiet `kupto.push` (konfiguracja VAPID, generator kluczy, subskrypcje, router, wysyłka), model `PushSubscription`, migracja `0005`, ustawienia `vapid_*`, `Notifier` w `app.state` i zamknięcie przy wyłączaniu aplikacji. Nowa zależność `pywebpush` (z `py-vapid`, `aiohttp`, `http-ece`).
- **API**: nowe endpointy `/api/push/*`; istniejące bez zmian.
- **Frontend**: obsługa `push` / `notificationclick` w `sw.ts`, moduł `pwa/push.ts`, komponent `NotificationSettings` na stronie gospodarstwa, wylogowanie wyłącza subskrypcję.
- **Wdrożenie**: zmienne `VAPID_*` w `deploy/docker-compose.yml`, `.env.example` i tabeli sekretów `deploy/README.md`; bez kluczy w SSM produkcja działa z wyłączonymi powiadomieniami.
- **Dane produkcyjne**: migracja tylko tworzy nową, pustą tabelę.

# Proposal

## Why

Podpowiedzi „to co zwykle” (#39) widać dopiero po otwarciu listy, a o zwykłych zakupach zapomina się właśnie wtedy, gdy nikt do aplikacji nie zagląda. Przypomnienie push „Zwykle o tej porze kupujecie mleko — dopisać?” (#40) przychodzi samo, raz dziennie i tylko wtedy, gdy jest coś nowego do przypomnienia.

## What Changes

- Nowy typ powiadomienia `usual_reminder` „Zwykłe produkty”: tytuł „Zwykle o tej porze kupujecie”, treść „mleko, chleb i 2 inne — dopisać do listy?”, kliknięcie otwiera listę z podpowiedziami (#39). Produkty z `usual_missing` (ta sama heurystyka co podpowiedzi przy liście i w czacie).
- Typ **domyślnie wyłączony** (włączany przełącznikiem na karcie „Powiadomienia”); obecni użytkownicy nie dostaną nowych powiadomień bez własnej decyzji.
- Limity: najwyżej **jedno przypomnienie dziennie na gospodarstwo** (doba w strefie Europe/Warsaw), wysyłane tylko między 9:00 a 21:00 czasu polskiego, i tylko gdy jest co najmniej jeden produkt, o którym gospodarstwo jeszcze nie dostało przypomnienia od ostatniego zakupu tego produktu. Te same produkty bez zmiany nie wracają.
- Przypomnienia wysyła komenda `python -m kupto.history.reminders` uruchamiana codziennie o 17:00 czasu polskiego przez nowy timer systemd `kupto-reminders.timer` (`docker compose exec` w kontenerze backendu).
- Nowa tabela `usual_reminders` (kiedy gospodarstwo dostało przypomnienie o danym produkcie) — migracja Alembic `0008`, wyłącznie addytywna.
- Poza zakresem: wybór godziny przypomnienia przez użytkownika, przypomnienia per użytkownik (osobne listy produktów), akcje w powiadomieniu („Dopisz” bez otwierania aplikacji), EventBridge Scheduler.

## Capabilities

### New Capabilities

(brak)

### Modified Capabilities

- `notifications`: przypomnienia push o zwykłych produktach i nowy, domyślnie wyłączony typ w ustawieniach. Capability powstaje w change `web-push` (jeszcze niezarchiwizowanym), więc wymagania są dopisywane jako ADDED.

## Impact

- **Backend**: `NotificationType.USUAL_REMINDER` i wpis `False` w `DEFAULT_ENABLED`; model `UsualReminder` i migracja `0008`; nowy moduł `kupto.history.reminders` (wybór produktów, limity, wysyłka, punkt wejścia CLI). `history/usual.py` bez zmian. Zależność `tzdata` (strefa czasowa niezależna od obrazu systemu).
- **API**: bez nowych endpointów; `GET /api/push/preferences` zwraca dodatkowy typ.
- **Frontend**: etykieta i opis nowego typu w `NotificationTypes.tsx`, typ w `api/types.ts`.
- **Wdrożenie**: `deploy/systemd/kupto-reminders.{service,timer}`, skrypt `deploy/kupto-reminders.sh`, wpisy w `kupto-update.sh` i `install.sh`, opis w `deploy/README.md`. Timer włącza się sam po wdrożeniu (mechanizm `timers` w `kupto-update.sh`).

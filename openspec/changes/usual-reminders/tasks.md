# Tasks

## 1. Backend: model i migracja

- [x] 1.1 Dodać model `UsualReminder` (`usual_reminders`) i migrację Alembic `0008` (`down_revision = "0007"`, wyłącznie addytywna) (design D3); weryfikacja: test w `tests/test_migrations.py` — upgrade 0007→0008 nie zmienia istniejących danych, tabela przyjmuje wpisy, PK `(household_id, normalized_name)` i FK działają, downgrade do 0007 i ponowny upgrade; `uv run alembic heads` pokazuje jedną głowę

## 2. Backend: przypomnienia (spec: notifications)

- [x] 2.1 Typ `NotificationType.USUAL_REMINDER` z `DEFAULT_ENABLED = False` (design D4); weryfikacja: testy API ustawień — typ widoczny i domyślnie wyłączony, można go włączyć
- [x] 2.2 Moduł `kupto.history.reminders`: wybór nowych produktów, limit dzienny i okno godzin w strefie Europe/Warsaw, blokada gospodarstwa, zapis `reminded_at`, adresaci z włączonym typem i subskrypcją, treść (design D2, D4, D5, D6); weryfikacja: testy — przypomnienie z treścią i tagiem, brak przypomnienia bez braków, izolacja gospodarstw, drugie uruchomienie tego samego dnia, te same produkty następnego dnia, nowy produkt, kolejny zakup, noc, typ wyłączony / tylko jeden domownik, włączenie po czasie, brak kluczy VAPID
- [x] 2.3 Punkt wejścia `python -m kupto.history.reminders` (ustawienia, logi JSON, `Notifier` z ustawień, zamknięcie połączeń) i zależność `tzdata`; weryfikacja: test wywołania `main` na bazie testowej

## 3. Frontend

- [x] 3.1 Etykieta i opis typu `usual_reminder` w `NotificationTypes.tsx` i `api/types.ts`; weryfikacja: test Vitest — przełącznik „Zwykłe produkty” widoczny i domyślnie odznaczony

## 4. Wdrożenie

- [x] 4.1 `deploy/systemd/kupto-reminders.{service,timer}` i `deploy/kupto-reminders.sh` (17:00 Europe/Warsaw, `Persistent=true`, blokada `/run/kupto.lock`), wpisy w `units`/`timers` w `kupto-update.sh` i w `install.sh`, opis w `deploy/README.md` (design D1); weryfikacja: `bash -n` skryptów, `systemd-analyze calendar '*-*-* 17:00:00 Europe/Warsaw'`

## 5. Integracja

- [x] 5.1 Uruchomić kroki CI lokalnie: `uv sync --locked`, `uv run ruff check`, `uv run ruff format --check`, `uv run pytest`, `npm ci`, `npx tsc -b`, `npm test`, `npx vite build`, oraz `uv run alembic heads`; weryfikacja: wszystkie przechodzą, jedna głowa migracji

## Workflow follow-up

- Zarchiwizować po change `web-push` (który tworzy capability `notifications`).
- Ręcznie na produkcji po wdrożeniu: `systemctl list-timers kupto-reminders.timer` pokazuje 17:00 czasu polskiego; po włączeniu typu i `systemctl start kupto-reminders` przypomnienie przychodzi na telefon (Android, iPhone PWA), a drugie uruchomienie nic nie wysyła.

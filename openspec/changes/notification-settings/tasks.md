# Tasks

## 1. Backend: model i migracja

- [ ] 1.1 Dodać model `NotificationPreference` (`notification_preferences`) i migrację Alembic `0007` (`down_revision = "0006"`, wyłącznie addytywna) (design D2); weryfikacja: test w `tests/test_migrations.py` — upgrade 0006→0007 nie zmienia istniejących danych, tabela przyjmuje ustawienia, PK `(user_id, type)` działa, downgrade do 0006 i ponowny upgrade; `uv run alembic heads` pokazuje jedną głowę

## 2. Backend: ustawienia i wysyłka (spec: notifications)

- [ ] 2.1 Moduł `kupto.push.preferences`: `DEFAULT_ENABLED`, odczyt ze wszystkimi typami, zapis (upsert), filtr `recipients_wanting`; `allowed_recipients` w `Notifier` korzysta z filtra (design D2, D3); weryfikacja: testy wysyłki — wyłączony typ pomija użytkownika przy wysyłce do gospodarstwa i do wskazanych, inny typ nadal przychodzi, ponowne włączenie, typ domyślnie wyłączony
- [ ] 2.2 Endpointy `GET /api/push/preferences` i `PUT /api/push/preferences/{type}` (design D4); weryfikacja: testy API — wartości domyślne, zmiana i idempotencja, izolacja użytkowników, 422 dla nieznanego typu, 401 bez logowania, działanie bez kluczy VAPID
- [ ] 2.3 Test przez REST: wyłączone „rozpoczęcie zakupów” u oli — `POST /api/list/shopping` ali nie wysyła na urządzenie oli, a zakończenie zakupów tak

## 3. Frontend

- [ ] 3.1 Przełączniki typów w `NotificationSettings` (zapytanie i mutacja z aktualizacją optymistyczną, wycofanie przy błędzie) (design D5); weryfikacja: testy Vitest — przełączniki widoczne w stanach „włączone”/„wyłączone”, zmiana wysyła `PUT`, błąd przywraca stan z komunikatem, brak przełączników przy niedostępnych powiadomieniach

## 4. Integracja

- [ ] 4.1 Uruchomić kroki CI lokalnie: `uv sync --locked`, `uv run ruff check`, `uv run ruff format --check`, `uv run pytest`, `npm ci`, `npx tsc -b`, `npm test`, `npx vite build`, oraz `uv run alembic heads`; weryfikacja: wszystkie przechodzą, jedna głowa migracji

## Workflow follow-up

- Zarchiwizować po change `web-push` (który tworzy capability `notifications`).
- #40: dodać typ przypomnień do `NotificationType`, `DEFAULT_ENABLED` (np. `False`) i etykiet frontendu — bez migracji.
- Ręcznie na produkcji: wyłączony typ nie przychodzi na telefon (Android, iPhone PWA).

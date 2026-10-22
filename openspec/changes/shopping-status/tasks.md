# Tasks

## 1. Backend: model i migracja

- [x] 1.1 Dodać `User.shopping_since` i migrację Alembic `0004` (`down_revision = "0003"`, kolumna `TIMESTAMPTZ NULL`) — design D1; weryfikacja: `uv run pytest` (migracje do `head` w fixture), `uv run alembic heads` pokazuje jedną głowę
- [x] 1.2 Rozszerzyć `tests/test_migrations.py`: upgrade `0003 → head` na bazie z danymi zachowuje dane i dodaje pustą kolumnę; downgrade do `0003` usuwa tylko kolumnę

## 2. Backend: status zakupów (spec: shopping-status)

- [x] 2.1 Moduł `kupto.lists.shopping_status` — `start`, `stop`, `active_shoppers`, `SHOPPING_STATUS_TTL` (design D2, D3); weryfikacja: testy serwisu — start i ponowny start bez zmiany `since`, stop, wygaśnięcie po 3 h, ponowny start po wygaśnięciu, izolacja gospodarstw
- [x] 2.2 `finish_shopping` zdejmuje status kończącego, odejście i usunięcie z gospodarstwa zdejmują status (design D4); weryfikacja: testy serwisu i API
- [x] 2.3 `ListOut.shoppers` oraz `POST` / `DELETE /api/list/shopping` (design D5); weryfikacja: testy API — widoczność dla domownika, brak dla innego gospodarstwa, kontrakt odpowiedzi

## 3. Czat (spec: needs-chat)

- [x] 3.1 Narzędzia `start_shopping` / `stop_shopping`, `shopping_now` w migawce, reguła promptu (design D6); weryfikacja: testy narzędzi i czatu z `FakeLLMClient`
- [x] 3.2 Ewaluacja „idę do sklepu” w `backend/evals/`; weryfikacja: uruchomienie z prawdziwym modelem

## 4. Frontend (spec: shopping-status)

- [x] 4.1 Przycisk „Idę na zakupy” / „Kończę” i wskaźnik, kto robi zakupy, w `ListView` (design D7); weryfikacja: testy Vitest, `npx tsc -b`, `npx vite build`

## 5. Integracja

- [x] 5.1 Kroki CI lokalnie: `uv sync --locked`, `uv run ruff check src tests evals`, `uv run ruff format --check src tests evals`, `uv run pytest`; frontend `npm ci`, `npx tsc -b`, `npm test`, `npx vite build`

## Workflow follow-up

- Po scaleniu PR zarchiwizować change (`/opsx:archive`), co utworzy `openspec/specs/shopping-status/spec.md` i doda wymaganie do `openspec/specs/needs-chat/spec.md`.

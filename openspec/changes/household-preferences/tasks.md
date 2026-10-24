# Tasks

## 1. Model i migracja (spec: household-preferences)

- [x] 1.1 `HouseholdPreferences` w `models.py`; migracja 0010 (addytywna) z testem upgrade/downgrade w `tests/test_migrations.py` (D1)

## 2. Backend (spec: household-preferences)

- [x] 2.1 `kupto/households/preferences.py`: walidacja i normalizacja, `load`, `save`, `for_model` (D1, D2)
- [x] 2.2 `GET`/`PUT /api/households/me/preferences`; testy API (izolacja gospodarstw, walidacja, brak preferencji)

## 3. Czat (spec: needs-chat — preferencje)

- [x] 3.1 Blok preferencji w instrukcjach (tylko niepuste), narzędzie `update_preferences` i zasada 4d (D3, D4); testy promptu, narzędzia i API z `FakeLLMClient`
- [x] 3.2 Ewaluacje: wykluczenie i dieta w propozycji, prośba o zapamiętanie → zapis z zachowaniem dotychczasowych, wzmianka bez prośby → bez zapisu

## 4. Frontend (spec: household-preferences)

- [x] 4.1 Sekcja „Preferencje” na stronie gospodarstwa, odświeżenie po wymianie w czacie (D5); testy Vitest

## 5. Integracja

- [x] 5.1 Kroki CI lokalnie: backend `uv sync --locked`, `ruff check`, `ruff format --check`, `pytest`; frontend `npm ci`, `npx tsc -b`, `npm test`, `npx vite build`

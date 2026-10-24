# Tasks

## 1. Model i migracja (spec: recipes)

- [x] 1.1 `Recipe`, `RecipeIngredient` w `models.py`; migracja 0009 (addytywna) z testem upgrade/downgrade w `tests/test_migrations.py` (D1)

## 2. Backend (spec: recipes)

- [x] 2.1 `kupto/recipes/library.py`: lista, odczyt, zapis, zmiana, usunięcie (izolacja gospodarstw, unikalna nazwa), `add_to_list` z notatką „na: <danie>” (D1–D3)
- [x] 2.2 `kupto/recipes/schemas.py`, `router.py` (`/api/recipes`, `/api/recipes/{id}/to-list`); testy API

## 3. Czat (spec: needs-chat — Przepisy gospodarstwa w czacie)

- [x] 3.1 Narzędzia `save_recipe`, `list_recipes`, `get_recipe` i zasada 4c w prompcie (D4); testy narzędzi, promptu i API z `FakeLLMClient`
- [x] 3.2 Ewaluacje: samo wklejenie przepisu nic nie zapisuje, „zapisz ten przepis” → zapis bez zmiany listy; zapisany przepis → propozycja, potwierdzenie → tylko brakujące z „na: <danie>”

## 4. Frontend (spec: recipes)

- [x] 4.1 Strona „Przepisy”: lista, szczegóły z dodaniem zaznaczonych składników, formularz dodania i edycji, usunięcie; link w nagłówku; unieważnienie przepisów po wymianie w czacie (D5); testy Vitest

## 5. Integracja

- [x] 5.1 Kroki CI lokalnie: backend `uv sync --locked`, `ruff check`, `ruff format --check`, `pytest`; frontend `npm ci`, `npx tsc -b`, `npm test`, `npx vite build`

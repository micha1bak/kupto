# Tasks

## 1. Model i migracja (spec: meal-plan)

- [ ] 1.1 `MealPlanEntry` w `models.py`; migracja 0011 (addytywna, po 0010) z testem upgrade/downgrade w `tests/test_migrations.py` (D1)

## 2. Backend (spec: meal-plan)

- [ ] 2.1 `kupto/meal_plan/service.py`: odczyt zakresu, ustawienie dni (upsert, przepis tylko z gospodarstwa, nazwa domyślnie z przepisu), usunięcie dnia (D1, D2)
- [ ] 2.2 `kupto/meal_plan/schemas.py`, `router.py` (`/api/meal-plan`); testy API

## 3. Czat (spec: needs-chat — Plan obiadów przez czat, Składniki z planu obiadów na listę)

- [ ] 3.1 Narzędzia `save_meal_plan`, `get_meal_plan`, data w instrukcjach i zasada 4e (D3); testy narzędzi, promptu i API z `FakeLLMClient`
- [ ] 3.2 Ewaluacje: prośba o plan → propozycja bez zapisu; potwierdzenie z poprawką → zapis z przepisem i pytanie o brakujące; odpowiedź → tylko brakujące z „na: <danie>”; pytanie o plan → odczyt

## 4. Integracja

- [ ] 4.1 Kroki CI lokalnie: backend `uv sync --locked`, `ruff check`, `ruff format --check`, `pytest`; frontend `npm ci`, `npx tsc -b`, `npm test`, `npx vite build`

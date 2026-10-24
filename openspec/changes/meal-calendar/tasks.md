# Tasks

## 1. Dane (spec: meal-plan — Kalendarz posiłków w aplikacji)

- [x] 1.1 Typy `MealPlanEntry`, `MealPlanDayInput`, klucz `keys.mealPlan` i `useMealPlan(from, to)`; daty lokalne w `mealPlan/dates.ts` z testami (D1, D4)

## 2. Widok (spec: meal-plan — Kalendarz posiłków w aplikacji)

- [x] 2.1 Wydzielenie `IngredientsToList` ze strony przepisu (D3)
- [x] 2.2 `MealPlanPage`: dwa tygodnie, nawigacja, link do przepisu, dodanie/zmiana/usunięcie dania, brakujące składniki (D1–D3); trasa `/meal-plan`, link na stronie „Przepisy”
- [x] 2.3 Odświeżenie planu po wymianie w czacie i usunięcie z cache przy utracie gospodarstwa (D4)
- [x] 2.4 Testy Vitest widoku; reguły szerokości 375 px (#76) (ręczny pomiar scrollWidth przy 375 px w przeglądarce — do wykonania przed merge)

## 3. Integracja

- [x] 3.1 Kroki CI frontendu lokalnie: `npm ci`, `npx tsc -b`, `npm test`, `npx vite build`

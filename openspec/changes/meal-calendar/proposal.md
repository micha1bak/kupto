# Proposal

## Why

Zmiana `dinner-plan` (#44) zapisuje plan obiadów gospodarstwa (dzień → danie) przez czat i udostępnia REST API `/api/meal-plan`, ale planu nie widać nigdzie poza rozmową, a poprawka jednego dnia wymaga pisania do asystenta. #47 (epik #41) dodaje kalendarz posiłków: widok zapisanego planu po tygodniach z ręczną edycją.

## What Changes

- Frontend: strona „Plan obiadów” (`/meal-plan`) — dwa tygodnie (bieżący i następny, od poniedziałku) jako pionowa lista dni z nawigacją o tydzień wstecz i w przód oraz powrotem do bieżącego tygodnia.
- Dzień pokazuje danie (link do przepisu, gdy danie ma przepis) i kto je zaplanował; dzień bez dania — przycisk dodania.
- Dodanie i zmiana dania: własna nazwa albo wybór z przepisów gospodarstwa (nazwa podpowiada się z przepisu); usunięcie dania z potwierdzeniem.
- Z dnia z przepisem: „Dodaj brakujące składniki” — ten sam przepływ co na stronie przepisu (zaznaczenie brakujących → zapotrzebowania z notatką „na: <danie>”); wspólny komponent wydzielony ze strony „Przepisy”.
- Dostęp przez link „Plan obiadów” na stronie „Przepisy” (bez linku w nagłówku — pasek nawigacji upraszcza #80).
- Odświeżenie planu po każdej wymianie w czacie (asystent może zapisać plan narzędziem `save_meal_plan`).
- Poza zakresem: zmiany backendu i migracje; kilka posiłków dziennie; przenoszenie dań między dniami; składniki kilku dań naraz; link w nagłówku (#80).

## Capabilities

### New Capabilities

_(brak)_

### Modified Capabilities

- `meal-plan`: nowe wymagania „Kalendarz posiłków w aplikacji” i „Edycja planu w kalendarzu” (capability wprowadza nie zmergowana jeszcze zmiana `dinner-plan`, więc wymagania są dopisane jako ADDED).

## Impact

- **Frontend**: nowy `mealPlan/MealPlanPage.tsx` (+ CSS, testy), `mealPlan/dates.ts`; wydzielony `recipes/IngredientsToList.tsx`; trasa `/meal-plan` w `App.tsx`; typy i zapytanie `useMealPlan` w `api/`; unieważnienie planu po wymianie w czacie (`ChatView.tsx`) i usunięcie z cache przy utracie gospodarstwa; link na stronie „Przepisy”.
- **Backend**: bez zmian — korzysta z `GET /api/meal-plan?from=&to=`, `PUT /api/meal-plan/{day}`, `DELETE /api/meal-plan/{day}` (#44) oraz `/api/recipes…` (#46).
- **Zależności**: wymaga zmiany `dinner-plan` (#44, PR #88), która stoi na `household-preferences` (#45, PR #87).
- **Koszt LLM**: brak.

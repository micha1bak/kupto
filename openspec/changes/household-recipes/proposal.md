# Proposal

## Why

Zmiany `recipe-text` (#42) i `recipe-link` (#43) zamieniają przepis na listę zakupów, ale przepis znika razem z rozmową. Gospodarstwa gotują w kółko te same dania, więc za każdym razem szukają przepisu od nowa. #46 (epik #41) wprowadza bazę „naszych przepisów” — wspólną dla gospodarstwa — z której da się szybko dodać brakujące składniki na listę i z której skorzystają plan obiadów (#44) i kalendarz posiłków (#47).

## What Changes

- Nowa encja przepisu gospodarstwa: nazwa (unikalna w gospodarstwie), liczba porcji, adres źródła, opis przygotowania i uporządkowana lista składników (nazwa, ilość i jednostka listy, notatka — np. miara kuchenna — oraz opcjonalna kategoria). Przepisy widzą i zmieniają wszyscy członkowie gospodarstwa.
- REST API `/api/recipes`: lista, szczegóły, dodanie, zmiana (zastąpienie całości), usunięcie oraz `POST /api/recipes/{id}/to-list` — dodanie wybranych składników jako zapotrzebowań autora z notatką „na: <danie>” (jak w zasadzie 4a z #42).
- Czat: narzędzia `save_recipe` (zapis na prośbę lub po potwierdzeniu użytkownika), `list_recipes` i `get_recipe` (tylko odczyt) oraz krótka zasada 4c w prompcie — zapis przepisu omawianego w rozmowie oraz „ugotujmy coś z naszych przepisów” → pytanie, czego brakuje → dodanie tylko brakujących.
- Frontend: strona „Przepisy” (lista, szczegóły z zaznaczaniem brakujących składników i dodaniem ich na listę, formularz dodania i edycji, usunięcie); link w nagłówku.
- Migracja 0009 (addytywna): tabele `recipes` i `recipe_ingredients`.
- Poza zakresem: plan obiadów (#44) i kalendarz (#47) — przygotowany jest tylko model danych; preferencje gospodarstwa (#45); zdjęcia, wyszukiwanie, tagi; przeliczanie porcji.

## Capabilities

### New Capabilities

- `recipes`: baza przepisów gospodarstwa i dodawanie składników przepisu na listę.

### Modified Capabilities

- `needs-chat`: nowe wymaganie „Przepisy gospodarstwa w czacie” (zapis przepisu z rozmowy, lista z zapisanego przepisu).

## Impact

- **Backend**: `models.py` (`Recipe`, `RecipeIngredient`), migracja `0009_household_recipes.py`, nowe moduły `kupto/recipes/library.py`, `schemas.py`, `router.py` (moduły z #43 — `fetch.py`, `extract.py`, `service.py` — bez zmian), narzędzia w `chat/tools.py`, zasada 4c w `chat/prompt.py`.
- **Frontend**: `recipes/RecipesPage.tsx`, trasy `/recipes…` w `App.tsx`, link w `MainPage.tsx`, typy i zapytania; odświeżenie przepisów po wymianie w czacie.
- **Zależności**: buduje na nie zmergowanych jeszcze zmianach `recipe-text` (#42) i `recipe-link` (#43) — zasada 4c odwołuje się do 4a i `fetch_recipe`.
- **Koszt LLM**: trzy nowe definicje narzędzi w każdym wywołaniu (kilkaset tokenów wejścia); zapis przepisu przez czat to dodatkowe tokeny wyjścia na składniki.

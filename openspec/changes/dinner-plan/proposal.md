# Proposal

## Why

Gospodarstwa co tydzień ustalają, co będzie na obiad, i dopiero potem wiedzą, co kupić. Asystent umie już zamienić pojedynczy przepis na listę (#42, #43), zna przepisy gospodarstwa (#46) i jego preferencje (#45), ale nie pomaga ułożyć kilku obiadów naraz, a ustalenia giną razem z rozmową. #44 (epik #41) wprowadza plan obiadów tworzony przez czat i zapisywany jako dane gospodarstwa, które pokaże i pozwoli edytować kalendarz posiłków (#47).

## What Changes

- Nowa encja planu obiadów: wpis „dzień → danie” (jeden obiad na dzień w gospodarstwie) z nazwą dania i opcjonalnym odwołaniem do przepisu gospodarstwa (`ON DELETE SET NULL` — po usunięciu przepisu danie zostaje w planie pod swoją nazwą). Plan jest wspólny dla gospodarstwa.
- REST API `/api/meal-plan` pod kalendarz (#47): odczyt planu z zakresu dat, ustawienie dania na dzień (zastępuje poprzednie) i usunięcie dnia.
- Czat: narzędzia `save_meal_plan` (zapis po potwierdzeniu propozycji; zwraca składniki dań z zapisanych przepisów) i `get_meal_plan` (tylko odczyt), bieżąca data w instrukcjach i krótka zasada 4e: prośba o plan na N dni → propozycja dań z datami (z przepisów gospodarstwa i/lub nowych, zgodnie z preferencjami) bez zapisu → po potwierdzeniu zapis → wypisanie składników i pytanie, czego brakuje → dodanie tylko brakujących z notatką „na: <danie>” (przepływ z #42/#46).
- Migracja 0011 (addytywna): tabela `meal_plan_entries`.
- Poza zakresem: widok kalendarza i ręczna edycja w UI (#47); kilka posiłków dziennie (śniadania, kolacje); usuwanie dni planu przez czat (w czacie dzień można nadpisać); śledzenie zapasów i sumowanie składników po stronie serwera.

## Capabilities

### New Capabilities

- `meal-plan`: plan obiadów gospodarstwa (dzień → danie) i jego API.

### Modified Capabilities

- `needs-chat`: nowe wymagania „Plan obiadów przez czat” i „Składniki z planu obiadów na listę”.

## Impact

- **Backend**: `models.py` (`MealPlanEntry`), migracja `0011_meal_plan.py`, nowy pakiet `kupto/meal_plan/` (`service.py`, `schemas.py`, `router.py`), narzędzia w `chat/tools.py`, data i zasada 4e w `chat/prompt.py`, data w `chat/router.py`.
- **Frontend**: bez zmian — plan pokaże kalendarz (#47).
- **Zależności**: buduje na nie zmergowanej zmianie `household-preferences` (#45, PR #87) — migracja 0011 następuje po 0010, a propozycje dań korzystają z preferencji w instrukcjach.
- **Koszt LLM**: dwie definicje narzędzi, jedno zdanie zasady i data (kilkanaście tokenów) w każdym wywołaniu; składniki dań zwracane od razu przez `save_meal_plan` oszczędzają rundy `get_recipe`.

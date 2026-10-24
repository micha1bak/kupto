# Design

## Context

Czat zamienia przepis na listę (zasady 4a/4b), zapisuje i odczytuje przepisy gospodarstwa (4c, `library`), a od #45 zna preferencje gospodarstwa (blok w instrukcjach). Brakuje planu: „co jemy w tym tygodniu” ustala się w rozmowie, ale nic tego nie zapamiętuje, a składniki kilku dań trzeba zbierać ręcznie. #47 pokaże plan w kalendarzu (widok tygodnia, ręczna edycja), więc model danych i API muszą to obsłużyć bez przebudowy.

## Goals / Non-Goals

**Goals:**
- Plan obiadów gospodarstwa (dzień → danie) tworzony przez czat po potwierdzeniu propozycji.
- Po zapisie planu: pytanie, czego brakuje, i dodanie tylko brakujących składników — tak jak dla przepisu (#42/#46).
- API odczytu po zakresie dat oraz ustawienia i usunięcia dnia — wystarczające dla kalendarza (#47).

**Non-Goals:**
- Kalendarz w UI (#47).
- Inne posiłki niż obiad, kilka dań dziennie, porcje na dzień.
- Usuwanie dni planu przez czat, sumowanie składników kilku dań po stronie serwera, śledzenie zapasów.

## Decisions

### D1. Model danych

`meal_plan_entries`: `id`, `household_id` (FK `CASCADE`), `day` (`DATE`), `name` (100), `recipe_id` (FK `recipes.id`, `ON DELETE SET NULL`, indeks), `planned_by_id` (FK `users.id`, `SET NULL`), `created_at`, `updated_at`; `UNIQUE (household_id, day)`.

- Jeden obiad na dzień: unikalność `(household_id, day)` upraszcza zapis (upsert „ustaw danie na dzień”) i kalendarz (dzień jest kluczem), a jej indeks obsługuje odczyt zakresu dat. Inne posiłki to w przyszłości addytywna kolumna `meal` z rozszerzeniem unikalności.
- `name` jest zawsze zapisana (przy daniu z przepisu domyślnie nazwa przepisu): danie bez przepisu ma tylko nazwę, a po usunięciu przepisu (`SET NULL`) danie zostaje w planie. Zmiana nazwy przepisu nie zmienia wpisu — kalendarz i tak linkuje po `recipe_id`.
- `day` to data kalendarzowa bez strefy; „dziś” liczymy w strefie `Europe/Warsaw` (jak przypomnienia o zwykłych zakupach).
- `planned_by_id` — kto ustawił obecne danie (dla kalendarza: „zaplanowała ala”).

Rozważone: plan jako osobna encja (tydzień) z pozycjami — dodatkowa tabela i pojęcie „aktywnego planu”, których kalendarz nie potrzebuje; plan to po prostu wpisy z datami.

### D2. API pod kalendarz (#47)

- `GET /api/meal-plan?from=YYYY-MM-DD&to=YYYY-MM-DD` — wpisy z zakresu (włącznie), rosnąco po dniu; dni bez obiadu pominięte. Zakres najwyżej 62 dni (`from` > `to` albo dłuższy zakres → 400).
- `PUT /api/meal-plan/{day}` `{name, recipe_id}` — ustawia danie na dzień (zastępuje poprzednie); wymagana nazwa lub przepis; przepis innego gospodarstwa → 404.
- `DELETE /api/meal-plan/{day}` — usuwa dzień; brak wpisu → 404.
- Odpowiedź wpisu: `id`, `day`, `name`, `recipe_id`, `planned_by` (login), `updated_at`.

Dzień zamiast identyfikatora w ścieżce: kalendarz operuje na dniach, a dzień jednoznacznie wskazuje wpis gospodarstwa. Serwis `kupto.meal_plan.service` (`list_entries`, `save_days`, `delete_day`) jest wspólny dla API i czatu. Zapis to `INSERT … ON CONFLICT (household_id, day) DO UPDATE` — równoczesne zapisy tego samego dnia nie kończą się błędem.

### D3. Czat: narzędzia, data i zasada 4e

- `save_meal_plan(days[{date, name, recipe_id}])` — 1–14 dni naraz, każdy dzień nadpisuje poprzednie danie. Daty spoza okna „dziś … dziś + 60 dni” są odrzucane (chroni przed pomyłką roku). Wynik: zapisane dni z dniem tygodnia, a przy daniach z przepisu także składniki — model od razu pyta o brakujące bez rund `get_recipe`. Nie zmienia listy.
- `get_meal_plan(date_from, date_to)` — tylko odczyt.
- W instrukcjach jedna linia z dzisiejszą datą i dniem tygodnia — bez niej model nie przeliczy „od poniedziałku” ani „na 5 dni” na daty.
- Zasada 4e: prośba o plan → `list_recipes`, propozycja po jednym obiedzie na dzień z datami (przepisy gospodarstwa i nowe dania, zgodnie z preferencjami z #45 — reguła preferencji już mówi o daniach), bez zapisu. Odpowiedź „tak” / „tak, ale w środę X” jest potwierdzeniem (jak zasada 4) → `save_meal_plan` → wypisanie składników (z wyniku narzędzia, a dla nowych dań typowe składniki) i pytanie, czego brakuje → dalej jak w 4a (tylko brakujące, notatka „na: <danie>”). Pytanie o plan → `get_meal_plan`.

Zapis planu łatwo poprawić (nadpisanie dnia w czacie, edycja w kalendarzu), więc jak przy przepisach (4c) nie potrzebuje oczekującej akcji w bazie. Dodawanie składników używa istniejącego `add_needs` z notatką — jak 4a/4c; `library.add_to_list` zostaje dla UI (#47 może go użyć przy dniu z przepisem).

Rozważone: osobne narzędzie „dodaj składniki planu na listę” wywołujące `library.add_to_list` — wymagałoby od modelu identyfikatorów składników i nie obsłużyłoby dań bez przepisu; `add_needs` obsługuje oba przypadki.

### D4. Frontend

Bez zmian w tej zmianie. Kalendarz (#47) doda zapytanie `['meal-plan', from, to]` i jego unieważnienie po wymianie w czacie (tak jak przepisy i preferencje).

## Risks / Trade-offs

- [Model zapisze plan bez potwierdzenia] → zasada wprost, ewaluacja sprawdza brak zapisu po samej prośbie o plan; plan łatwo nadpisać.
- [Model poda zły rok lub dzień tygodnia] → data i dzień tygodnia w instrukcjach, okno dat w narzędziu, dzień tygodnia w wyniku narzędzia.
- [Więcej tokenów w każdej rozmowie] → dwie krótkie definicje narzędzi, zasada w kilku zdaniach, data w jednej linii.
- [Zależność od nie zmergowanego #87] → migracja 0011 po 0010; po merge #87 rebase na `main`.

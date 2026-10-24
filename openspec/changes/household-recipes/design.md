# Design

## Context

Przepis trafia dziś do czatu jako wklejony tekst (zasada 4a, #42) albo link (zasada 4b, narzędzie `fetch_recipe`, #43). Asystent wypisuje składniki, pyta, czego brakuje, i dodaje tylko brakujące jako zapotrzebowania autora z notatką „na: <danie>”. Nic nie jest zapamiętywane. Następne zadania epiku #41 potrzebują trwałych przepisów: plan obiadów (#44) zapisuje „dzień → danie” i dodaje składniki z planu na listę, kalendarz (#47) pokazuje i edytuje plan.

## Goals / Non-Goals

**Goals:**
- Wspólna baza przepisów gospodarstwa: dodawanie i edycja w UI, zapis przez czat.
- Z zapisanego przepisu: wybór brakujących składników → zapotrzebowania z notatką „na: <danie>” (UI i czat).
- Model danych, do którego #44/#47 mogą się odwołać bez przebudowy.

**Non-Goals:**
- Encja planu posiłków (#44) i widok kalendarza (#47).
- Przeliczanie porcji, wyszukiwanie, tagi, zdjęcia, import wielu przepisów naraz.
- Zmiana zachowania `fetch_recipe` i zasad 4a/4b.

## Decisions

### D1. Model danych

`recipes`: `id`, `household_id` (FK, `ON DELETE CASCADE`), `name` (100), `normalized_name` (100, unikalna w gospodarstwie — jak `list_items`), `servings` (tekst do 50 znaków, np. „4 porcje”, „10 sztuk” — tak podaje go schema.org `recipeYield`), `source_url` (do 2000 znaków, tylko http/https), `instructions` (tekst do 8000 znaków — tyle co wiadomość czatu), `created_by_id` (FK `SET NULL`), `created_at`, `updated_at`.

`recipe_ingredients`: `id`, `recipe_id` (FK `CASCADE`, indeks), `position` (kolejność z przepisu), `name` (100), `amount` (`Numeric(10,3)`), `unit` (istniejący enum `unit`), `note` (200), `category` (istniejący enum `category`, opcjonalna).

Pola składnika odpowiadają `NeedCreate` — składnik zamienia się w zapotrzebowanie bez przeliczeń. Miary kuchenne (łyżka, szklanka) trafiają do `note`, jak w zasadzie 4a. Kategoria jest opcjonalna: czat ją podaje, formularz w UI nie (przy dodaniu na listę zadziała pamięć kategorii gospodarstwa).

Rozważone: składniki jako JSONB w `recipes` — prościej, ale #44 będzie chciał zsumować składniki kilku dań i odwoływać się do nich zapytaniami; osobna tabela jest spójna z resztą modelu (`needs`, `purchased_needs`).

**Pod #44/#47**: wpis planu będzie miał `recipe_id` (FK `recipes.id`, `ON DELETE SET NULL`) i własną nazwę dania (danie bez zapisanego przepisu albo przepis później usunięty). Identyfikator przepisu jest stabilny — edycja zmienia przepis w miejscu. Dodawanie składników na listę to funkcja serwisu `library.add_to_list(session, household, user, recipe_id, ingredient_ids)`, którą plan wywoła dla każdego dania. Unikalna nazwa w gospodarstwie pozwala czatowi odnaleźć przepis po nazwie dania.

### D2. Edycja zastępuje całość

`PUT /api/recipes/{id}` zastępuje pola i całą listę składników (nowe identyfikatory składników). Formularz i tak wysyła całość; częściowe zmiany pojedynczych składników nie są potrzebne. Składniki nie są celem odwołań z innych tabel (plan odwołuje się do przepisu), więc zmiana ich identyfikatorów niczego nie psuje.

### D3. Dodanie na listę

`POST /api/recipes/{id}/to-list` z `ingredient_ids` (1–60, muszą należeć do przepisu — inaczej 404) dodaje zapotrzebowania autora przez `lists.service.add_needs` (scalanie z istniejącą pozycją, `already_on_list`, zdarzenie zmiany listy) i wysyła powiadomienie „dodano produkty” jak przy ręcznym dodaniu. Notatka: „na: <nazwa>” albo „na: <nazwa> (<notatka składnika>)”, przycięta do 200 znaków — tak samo jak w zasadzie 4a. Odpowiedź: dodane pozycje z flagą `already_on_list`.

Użytkownik wybiera brakujące składniki (domyślnie nic nie jest zaznaczone) — jak w przepływie z #42 („pytaj, czego brakuje”), bez śledzenia zapasów.

### D4. Czat: narzędzia i zasada 4c

- `save_recipe(name, servings, source_url, instructions, ingredients[])` — zapisuje przepis; nazwa zajęta → `{"error": ...}` (model mówi o tym użytkownikowi). Nie zmienia listy (`list_changed` = false).
- `list_recipes()` — nazwy i identyfikatory (najwyżej 100, alfabetycznie), tylko odczyt.
- `get_recipe(recipe_id)` — składniki, porcje, źródło i opis, tylko odczyt; przepis innego gospodarstwa → błąd „nie ma takiego przepisu”.

Zasada 4c: zapis tylko na prośbę użytkownika (np. „zapisz ten przepis”) albo po potwierdzeniu propozycji zapisu — tak jak inne zmiany danych (prośba wprost jak w zasadzie 3, propozycja wymaga potwierdzenia jak w zasadzie 4). Zapis łatwo cofnąć (usunięcie w UI), więc nie potrzebuje oczekującej akcji w bazie jak zakończenie zakupów. Zapisuje się **wszystkie** składniki (także woda, sól, pieprz — pomija się je tylko przy propozycji zakupów). „Zróbmy X z naszych przepisów” → `list_recipes`/`get_recipe` → dalej jak w zasadzie 4a.

Rozważone: zapis bez udziału modelu (przycisk „zapisz” przy wiadomości) — wymagałby parsowania przepisu po stronie serwera; model i tak już wyciąga składniki w 4a/4b.

### D5. Frontend

Trasy `/recipes` (lista), `/recipes/new`, `/recipes/:id`, `/recipes/:id/edit` w jednym module `recipes/RecipesPage.tsx`; link „Przepisy” w nagłówku. Szczegóły: składniki z polami wyboru, przycisk „Dodaj zaznaczone na listę”, komunikat z wynikiem. Formularz: wiersze składników (nazwa, ilość, jednostka, notatka) z dodawaniem i usuwaniem. Po każdej wymianie w czacie zapytanie o przepisy jest unieważniane (przepis mógł zostać zapisany przez czat).

## Risks / Trade-offs

- [Model zapisze przepis bez prośby] → zasada wprost; zapis łatwo usunąć w UI; ewaluacja sprawdza brak zapisu po samym wklejeniu przepisu.
- [Model źle rozbije składnik z linku na ilość i jednostkę] → miary kuchenne idą do notatki, jak w 4a; użytkownik może poprawić przepis w UI.
- [Więcej narzędzi = więcej tokenów na wywołanie] → trzy krótkie definicje; `list_recipes` zwraca tylko nazwy.
- [Zależność od nie zmergowanych #83/#84] → po ich merge rebase; zmiana nie modyfikuje ich kodu.

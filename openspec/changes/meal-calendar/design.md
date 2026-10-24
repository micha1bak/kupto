# Design

## Context

`dinner-plan` (#44) daje plan obiadów: najwyżej jedno danie na dzień (nazwa + opcjonalny `recipe_id`, `planned_by`), odczyt zakresu dat (włącznie, do 62 dni, dni bez obiadu pominięte), `PUT` dnia (zastępuje, nazwa domyślnie z przepisu) i `DELETE` dnia (404, gdy pusty). Strona „Przepisy” (#46) ma już przepływ „zaznacz, czego brakuje → dodaj na listę” (`POST /api/recipes/{id}/to-list`). Frontend to React + TanStack Query, PWA używana głównie na telefonie (szerokość 375 px bez przewijania w bok, #76).

## Goals / Non-Goals

**Goals:**
- Podgląd planu na najbliższe dni i przeglądanie po tygodniach.
- Ręczna edycja dnia: dodanie, zmiana (nazwa lub przepis), usunięcie z potwierdzeniem.
- Z dania z przepisem — dodanie brakujących składników bez przechodzenia do przepisu.

**Non-Goals:**
- Zmiany API planu, kilka posiłków dziennie, przenoszenie dań między dniami.
- Zbiorcze składniki z całego tygodnia (robi to czat, zasada 4e).
- Link w nagłówku (#80 przebudowuje nawigację).

## Decisions

### D1. Dwa tygodnie jako pionowa lista

Widok obejmuje 14 dni od poniedziałku wybranego tygodnia (domyślnie bieżącego) — jedno zapytanie `GET /api/meal-plan?from=<pon>&to=<pon + 13>`, daleko poniżej limitu 62 dni. Dni to pionowa lista w dwóch kartach (po tygodniu, z zakresem dat w nagłówku), nie tabela 7 kolumn — na 375 px tabela nie zmieści nazw dań. Nawigacja przesuwa o jeden tydzień („← Wcześniej”, „Później →”), „Ten tydzień” wraca do dziś. Dzisiejszy dzień jest wyróżniony.

Daty liczone w czasie lokalnym przeglądarki jako `YYYY-MM-DD` (bez `Date.toISOString()`, które przesuwa dzień przez UTC). Serwer liczy „dziś” w strefie Europe/Warsaw — dla gospodarstw w Polsce to ta sama data.

Rozważone: tydzień jako siatka 7 kolumn na desktopie — dodatkowy układ do utrzymania przy niewielkim zysku; aplikacja jest używana głównie na telefonie.

### D2. Edycja w miejscu

„Dodaj danie”/„Zmień” rozwija w wierszu dnia formularz: lista „Przepis” (przepisy gospodarstwa, opcja „— bez przepisu —”) i pole „Danie”. Wybór przepisu wpisuje jego nazwę, gdy pole jest puste albo zawiera nazwę poprzednio wybranego przepisu — własnej nazwy nie nadpisuje. Zapis: `PUT /api/meal-plan/{dzień}` z `{name, recipe_id}`; puste pole nazwy przy wybranym przepisie wysyła `name: null` (serwer bierze nazwę przepisu). Bez nazwy i przepisu — komunikat w formularzu, bez żądania. Usunięcie: `window.confirm` (jak usunięcie przepisu), potem `DELETE`. Po zapisie i usunięciu unieważniamy `keys.mealPlan` (wszystkie zakresy). Naraz otwarty jest jeden formularz albo jedna lista składników.

### D3. Brakujące składniki — wspólny komponent

Sekcja „Składniki” ze strony przepisu (zaznaczanie, „Dodaj zaznaczone na listę”, komunikat `addedMessage`) staje się komponentem `IngredientsToList` (`recipes/IngredientsToList.tsx`), używanym przez stronę przepisu i kalendarz. W kalendarzu „Dodaj brakujące składniki” rozwija pod dniem ten komponent dla przepisu dania (pobranego `useRecipe`, więc wspólny cache z przepisami). Notatka „na: <danie>” pochodzi z nazwy przepisu (serwer, #46) — bez zmian API.

### D4. Odświeżanie

Klucz `keys.mealPlan = ["meal-plan"]`, zapytania `[...keys.mealPlan, from, to]`. `ChatView` po każdej wymianie unieważnia też `keys.mealPlan` (narzędzie `save_meal_plan` nie wysyła sygnału zmiany listy), a utrata gospodarstwa usuwa te dane z cache, jak pozostałe.

## Risks / Trade-offs

- [Przepis usunięty po wczytaniu planu] → link prowadzi do błędu strony przepisu; po ponownym wczytaniu planu `recipe_id` jest `null`. Akceptowalne.
- [Równoczesna edycja przez dwóch domowników] → ostatni zapis wygrywa (upsert w #44); widok odświeża się po własnych zmianach i po powrocie do karty.
- [Zależność od nie zmergowanego #88] → PR do `main` z notką; merge po #87 i #88.

# Design

## Context

Historia zakupów żyje w trzech tabelach z #36: `shopping_trips` (gospodarstwo, `finished_at`, `finished_by_id`, indeks `(household_id, finished_at)`), `purchased_items` (nazwa, `normalized_name`, kategoria, `bought_at`, `bought_by_id`) i `purchased_needs` (zgłaszający, ilość, jednostka, notatka, `requested_at`). Modele nie mają relacji do `User`, a autorzy mogą być NULL (konto usunięte — `ON DELETE SET NULL`). Lista bieżąca grupuje pozycje po kategoriach w kolejności użytkownika (`category_order.get_order`) i sumuje ilości przez `aggregate_quantities`. Na produkcji są prawdziwe dane; ta zmiana nie może wymagać migracji.

## Goals / Non-Goals

**Goals:**
- Czytelny na telefonie przegląd zakończeń zakupów, od najnowszych, doczytywany porcjami.
- Szybka odpowiedź „kiedy i kto ostatnio kupił X”.

**Non-Goals:**
- Kwoty, wydatki, statystyki; edycja i usuwanie historii.
- Indeksy i rozszerzenia bazy (`unaccent`, `pg_trgm`) — wymagałyby migracji.

## Decisions

### D1. Osobny moduł `kupto.history` z routerem `/api/history`

Historia to odczyt, nie stan listy — `kupto.lists.service` pozostaje „jedynym miejscem, w którym zmienia się stan listy”. Router wymaga gospodarstwa (`CurrentHousehold`), a każde zapytanie filtruje po `ShoppingTrip.household_id`.

### D2. Paginacja kursorem po `(finished_at, id)`, kursor = id zakończenia

Kolejność: `finished_at DESC, id DESC`. Kursor `before` to id ostatniego zakończenia z poprzedniej strony; serwer odczytuje jego `finished_at` (tylko w obrębie gospodarstwa — obcy lub nieistniejący kursor daje 404) i zwraca zakończenia z `(finished_at, id) < (kursor)`. Odpowiedź: `{trips, next_cursor}`; `next_cursor` jest NULL, gdy nie ma więcej. Pobieramy `limit + 1` wierszy, żeby wiedzieć, czy jest następna strona. Kursor-id jest krótki, nie wymaga kodowania daty w URL i jest stabilny przy dopisywaniu nowych zakończeń (offset przesuwałby strony). `limit` domyślnie 10, maks. 50. Zapytanie korzysta z istniejącego indeksu `(household_id, finished_at)`.

### D3. Kształt zakończenia w odpowiedzi

`TripOut`: `id`, `finished_at`, `finished_by` (login lub NULL), `item_count`, `groups` — kategorie w kolejności użytkownika (jak lista), w grupie pozycje alfabetycznie po `normalized_name`. Pozycja: `id`, `name`, `category`, `bought_at`, `bought_by`, `quantities` (z `aggregate_quantities`), `needs` (`login`, `amount`, `unit`, `note`, `requested_at`). Loginy pobieramy jednym zapytaniem `id → login` dla wszystkich autorów na stronie zamiast dodawać relacje do modeli.

### D4. Wyszukiwanie bez rozszerzeń bazy

Porównanie: `translate(lower(normalized_name), 'ąćęłńóśźż', 'acelnoszz') LIKE '%fraza%'`, gdzie fraza przechodzi tę samą normalizację w Pythonie (`normalize_name` + zamiana polskich znaków), a `%`, `_` i `\` są escapowane. `translate` jest wbudowane w PostgreSQL — nie potrzeba `unaccent` ani migracji. Wynik grupujemy po `normalized_name` funkcjami okna: `row_number()` (ostatni zakup wg `bought_at DESC, id DESC`) i `count()` (ile razy kupowany); zwracamy najwyżej 20 produktów, ostatnio kupione pierwsze. Dla każdego: `name`, `category`, `last_bought_at`, `last_bought_by`, `last_trip_id`, `times_bought`, `last_quantities`. Pusta fraza (po przycięciu) zwraca 422.

**Propozycja na później:** przy dużej historii indeks GIN `pg_trgm` na `translate(lower(normalized_name), …)` (wymaga `CREATE EXTENSION pg_trgm` i migracji) albo kolumna z nazwą bez znaków diakrytycznych.

### D5. Frontend: osobna strona `/history`

Wzorem strony gospodarstwa: trasa `/history` w `App.tsx`, link „Historia” w nagłówku `MainPage`, na stronie „← Wróć do listy”. `useInfiniteQuery` (`["history"]`) z `next_cursor` jako `pageParam` i przyciskiem „Pokaż więcej”. Pole wyszukiwania z opóźnieniem ~300 ms; przy niepustej frazie zamiast zakończeń widać wyniki wyszukiwania (`["history-search", fraza]`). Daty po polsku (`Intl.DateTimeFormat("pl-PL")`, np. „śr., 21 paź, 18:30”). Zakończenie to sekcja (karta) z datą i „zakończył(a): login”, w niej nagłówki kategorii i pozycje: nazwa, suma ilości, kto i o której kupił, zgłaszający z notatkami.

## Risks / Trade-offs

- **Skan przy wyszukiwaniu** → historia jednego gospodarstwa jest mała (dziesiątki pozycji tygodniowo); filtr po gospodarstwie idzie przez `shopping_trips`. Indeks trigramowy opisany jako propozycja.
- **`translate` obejmuje tylko polskie znaki** → wystarczające dla tej aplikacji; inne znaki diakrytyczne porównywane dosłownie.
- **Kolejność kategorii użytkownika zmienia się w czasie** → historia zawsze pokazuje bieżącą kolejność, spójnie z listą.

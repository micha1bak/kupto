# Proposal

## Why

Lista jest dziś zawsze pogrupowana w tej samej, stałej kolejności kategorii, która rzadko odpowiada układowi sklepu, w którym akurat robi się zakupy — w sklepie trzeba przewijać listę w tę i z powrotem. Każdy domownik chodzi po sklepie po swojemu, więc chce sam ustawić kolejność kategorii, i to bez czekania, aż aplikacja nauczy się jej z historii zakupów (#38).

## What Changes

- Użytkownik może przeciągnąć nagłówek kategorii na liście w inne miejsce; kategoria zostaje **przypięta** na tym miejscu. Przeciąganie startuje dopiero po przytrzymaniu nagłówka, żeby w sklepie nie przesunąć niczego przypadkiem (zwykłe przewijanie i stuknięcia działają jak dotąd); jest też alternatywa z klawiatury.
- Kolejność jest **per użytkownik**, a nie per gospodarstwo: przypięcia jednego domownika nie zmieniają listy pozostałych. Zawartość wspólnej listy pozostaje identyczna dla wszystkich członków — różnić może się tylko kolejność grup.
- Przypięte kategorie mają pierwszeństwo: zajmują swoje miejsca, a nieprzypięte układają się wokół nich w kolejności automatycznej (dziś: obecnej, stałej kolejności kategorii; w przyszłości: kolejności wyuczonej, #38).
- Akcje „Odepnij” (pojedyncza kategoria) oraz „Przywróć automatyczną kolejność” (wszystkie przypięcia użytkownika).
- Lista zwracana przez API jest uporządkowana według kolejności zalogowanego użytkownika, a każda grupa ma znacznik, czy jest przypięta. Nowe endpointy do odczytu pełnej kolejności oraz do przypinania, odpinania i resetu.
- Nowa tabela przypięć w bazie (migracja Alembic) i nowa zależność frontendu do przeciągania (`@dnd-kit`).

## Capabilities

### New Capabilities

<!-- Brak — kolejność kategorii jest częścią prezentacji wspólnej listy zakupów. -->

### Modified Capabilities

- `shopping-list`: lista członków jest identyczna co do zawartości, ale kolejność grup kategorii jest per użytkownik; nowe wymagania: automatyczna kolejność kategorii, przypinanie kategorii przeciągnięciem nagłówka (z przytrzymaniem), pierwszeństwo przypiętych kategorii, odpinanie i przywracanie automatycznej kolejności.

## Impact

- **Backend**: nowy model i tabela `user_category_pins` (migracja `0002`), moduł wyliczania kolejności (przypięcia + kolejność bazowa) gotowy na połączenie z kolejnością wyuczoną (#38) i na kolejność produktów (#34); `GET /api/list` sortuje grupy według użytkownika i zwraca `pinned`; nowe endpointy `GET /api/list/category-order`, `PUT /api/list/category-order/{category}`, `DELETE /api/list/category-order/{category}`, `DELETE /api/list/category-order`.
- **Frontend**: przeciągane nagłówki kategorii w `ListView`, przycisk odpinania i resetu, optymistyczna aktualizacja; nowe zależności `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities`.
- **API**: zmiana zgodna wstecz — `GET /api/list` dostaje pole `pinned` w grupach; bez przypięć kolejność jest taka jak dotąd.
- **Czat**: bez zmian — asystent widzi listę w kolejności automatycznej.

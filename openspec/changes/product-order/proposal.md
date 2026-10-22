# Proposal

## Why

Od #33 każdy domownik może ułożyć kategorie w kolejności swojego sklepu, ale w obrębie kategorii produkty są zawsze alfabetycznie. W większych działach (np. Nabiał, Warzywa i owoce) półki też mają swój porządek — kto zna sklep, chce mieć „mleko” przed „jogurtem”, bo tak po nie sięga. Ręczna kolejność produktów (#34) domyka ręczne układanie listy, zanim aplikacja nauczy się kolejności z historii zakupów (#38).

## What Changes

- Użytkownik może przeciągnąć produkt (za uchwyt w wierszu) w inne miejsce **w obrębie jego kategorii**; produkt zostaje **przypięty** na tym miejscu. Na dotyku przeciąganie startuje dopiero po przytrzymaniu uchwytu, więc odhaczanie i przewijanie listy w sklepie działają jak dotąd; jest też obsługa z klawiatury.
- Kolejność jest **per użytkownik** i zapamiętana **per produkt** (znormalizowana nazwa), więc działa także przy kolejnym dodaniu tego samego produktu na listę, np. w następnym tygodniu.
- Przypięte produkty mają pierwszeństwo, a nieprzypięte układają się wokół nich w kolejności bazowej — dziś alfabetycznej, w przyszłości wyuczonej (#38).
- Akcja „Odepnij” przy przypiętym produkcie (wraca na miejsce z kolejności bazowej).
- Każda pozycja w odpowiedzi listy dostaje znacznik `pinned`; pozycje w grupie są uporządkowane według kolejności zalogowanego użytkownika. Nowe endpointy przypinania i odpinania produktu.
- Nowa tabela przypięć produktów (migracja Alembic `0006`, wyłącznie addytywna).
- Poza zakresem: przenoszenie produktu do innej kategorii przeciąganiem, kolejność wyuczona (#38), reset kolejności wszystkich produktów jednym przyciskiem.

## Capabilities

### New Capabilities

<!-- Brak — kolejność produktów jest częścią prezentacji wspólnej listy zakupów. -->

### Modified Capabilities

- `shopping-list`: zawartość listy pozostaje wspólna, ale kolejność pozycji w grupie i ich znacznik przypięcia są per użytkownik; nowe wymagania: kolejność produktów w kategorii, przypinanie produktu przeciągnięciem (z przytrzymaniem, tylko w obrębie kategorii), pierwszeństwo przypiętych produktów, odpinanie produktu.

## Impact

- **Backend**: model i tabela `user_product_pins` (migracja `0006`), moduł `kupto.lists.product_order` korzystający z istniejącej funkcji `arrange` (kolejność bazowa w jednym miejscu — punkt podpięcia #38); `list_out` porządkuje pozycje w grupie i zwraca `pinned`; endpointy `PUT /api/list/items/{item_id}/order` i `DELETE /api/list/items/{item_id}/order`; publikacja `order_changed` (lista na żywo u tego użytkownika).
- **Frontend**: przeciągane wiersze produktów (zagnieżdżone sortowanie w każdej grupie kategorii, bez zmian w przeciąganiu nagłówków), znacznik 📌 i „Odepnij”, optymistyczna aktualizacja.
- **API**: zmiana zgodna wstecz — nowe pole `pinned` w pozycjach; bez przypięć kolejność jak dotąd (alfabetycznie).
- **Czat**: bez zmian — asystent widzi pozycje w kolejności bazowej.

# Proposal

## Why

Kolejność kategorii i produktów na liście jest dziś stała (kategorie w kolejności zbioru, produkty alfabetycznie), a dopasowanie jej do sklepu wymaga ręcznego przeciągania (#33, #34). Historia zakupów (#36) zapisuje dla każdej kupionej pozycji, kto i kiedy ją odhaczył — czyli kolejność, w jakiej domownik przechodzi przez sklep. Lista może się tej kolejności nauczyć sama, osobno dla każdego użytkownika, bo każdy chodzi do sklepu inaczej (#38).

## What Changes

- **Kolejność wyuczona** zastępuje stałą kolejność bazową kategorii i alfabetyczną kolejność produktów: liczona z kolejności odhaczeń zalogowanego użytkownika w jego ostatnich zakończeniach zakupów (mediana względnego miejsca z ostatnich 10 przejść przez sklep).
- **Zimny start**: gdy użytkownik ma mniej niż 3 własne przejścia, kolejność uczy się z odhaczeń wszystkich członków gospodarstwa; bez nich zostaje dotychczasowa kolejność (stała dla kategorii, alfabetyczna dla produktów). Kategorie i produkty, o których historia nic nie mówi, zostają na swoich miejscach z kolejności dotychczasowej.
- **Stabilność**: kolejność zmienia się tylko po zakończeniu zakupów (nie przy każdym odhaczeniu), a mediana z 10 przejść sprawia, że jedno nietypowe przejście jej nie przestawia.
- **Przypięcia ręczne mają pierwszeństwo** bez zmian w ich modelu i API: przypięte kategorie (#33) i produkty (#34) układają się jak dotąd, a nieprzypięte wypełniają resztę w kolejności wyuczonej.
- Bez zmian schematu bazy (bez migracji) — kolejność liczona w locie z historii.
- Poza zakresem: kolejność per sklep, dzielenie jednego zakończenia zakupów na kilka wizyt w sklepie, zmiany w UI (kolejność wyuczona to nadal „automatyczna kolejność”), kolejność użytkownika w czacie.

## Capabilities

### New Capabilities

_(brak)_

### Modified Capabilities

- `shopping-list`: kolejność automatyczna kategorii staje się kolejnością wyuczoną z odhaczeń użytkownika (z zimnym startem); nowe wymaganie — wyuczona kolejność kategorii i produktów, jej źródło, zimny start, stabilność i pierwszeństwo przypięć.

## Impact

- **Backend**: nowy moduł `kupto.lists.learned_order` (odczyt przejść z historii i wyliczenie wyników), czysta funkcja `learned` w `kupto.lists.ordering`; `category_order` i `product_order` używają kolejności wyuczonej jako bazowej — w odczycie listy, odczycie kolejności kategorii, przypinaniu kategorii i produktów oraz w kolejności kategorii w historii. Bez migracji.
- **API**: bez zmian kształtu odpowiedzi; zmienia się tylko kolejność grup i pozycji dla użytkowników z historią odhaczeń.
- **Frontend**: bez zmian.
- **Czat**: bez zmian — asystent widzi pozycje w kolejności bazowej.

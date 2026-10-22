# Proposal

## Why

Domownicy nie wiedzą, że ktoś właśnie jest w sklepie, więc nie dopisują brakujących rzeczy w porę, a dwie osoby potrafią pójść na te same zakupy (#28). Status „robię zakupy” jest też podstawą zapowiedzianych powiadomień push: „X idzie na zakupy” (#29), „Dopisano w trakcie” — tylko do osób ze statusem (#30) i „Zakupy zakończone” (#31).

## What Changes

- Lekki status użytkownika „robię zakupy” zamiast pełnego modelu „wyprawy na zakupy”: członek gospodarstwa włącza go przyciskiem „Idę na zakupy” albo w czacie („idę do sklepu”, „jestem w sklepie”), wyłącza przyciskiem „Kończę” albo w czacie, a zakończenie zakupów zdejmuje go automatycznie.
- Status sam wygasa po 3 godzinach — liczone przy odczycie, bez zadań w tle.
- Domownicy widzą, kto teraz robi zakupy i od kiedy: lista zwracana przez API zawiera aktywne statusy członków, a UI pokazuje wskaźnik „Ania robi zakupy” nad listą.
- Asystent ma narzędzia `start_shopping` / `stop_shopping` i regułę w prompcie; w migawce listy widzi, kto robi zakupy.
- Opuszczenie gospodarstwa (lub usunięcie z niego) zdejmuje status.
- Nowa kolumna `users.shopping_since` (migracja Alembic `0004`, wyłącznie addytywna, dopuszcza NULL).
- Poza zakresem: same powiadomienia push (#29–#31) i historia statusów.

## Capabilities

### New Capabilities

- `shopping-status`: status członka gospodarstwa „robię zakupy” — włączanie, wyłączanie, wygasanie i widoczność dla domowników; punkt odczytu dla przyszłych powiadomień.

### Modified Capabilities

- `needs-chat`: nowe wymaganie — asystent włącza i wyłącza status zakupów na prośbę użytkownika.

## Impact

- **Backend**: kolumna `users.shopping_since` (migracja `0004`), moduł `kupto.lists.shopping_status` (start, stop, aktywni kupujący, chwila wygaśnięcia), `service.finish_shopping` zdejmuje status kończącego, `households` zdejmuje status przy odejściu z gospodarstwa, narzędzia czatu `start_shopping` / `stop_shopping`, reguła promptu, pole `shopping_now` w migawce listy dla modelu.
- **API**: `ListOut` (wszystkie odpowiedzi `/api/list…`) dostaje pole `shoppers`; nowe `POST /api/list/shopping` i `DELETE /api/list/shopping` zwracające listę. Zmiana addytywna — istniejący klienci działają bez zmian.
- **Frontend**: przycisk „Idę na zakupy” / „Kończę” w pasku narzędzi listy i wskaźnik, kto robi zakupy (`ListView`), typ `ShoppingList.shoppers`.
- **Dane produkcyjne**: migracja tylko dodaje pustą (NULL) kolumnę; istniejące dane nie są zmieniane.

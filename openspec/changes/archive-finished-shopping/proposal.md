# Proposal

## Why

„Zakończ zakupy” dziś bezpowrotnie usuwa kupione pozycje, więc gospodarstwo traci informację, co, kiedy i przez kogo zostało kupione. Ta informacja jest fundamentem kolejnych funkcji epiku #35: widoku historii zakupów (#37), wyuczonej kolejności kategorii i produktów per użytkownik (#38) i podpowiedzi „to co zwykle” (#39) — bez jej zapisywania każdy dzień użycia aplikacji to utracone dane do nauki.

## What Changes

- Zakończenie zakupów **przenosi** kupione pozycje do historii zakupów gospodarstwa zamiast je usuwać; z aktywnej listy znikają jak dotąd, a niekupione pozycje zostają bez zmian.
- Każde zakończenie zakupów tworzy w historii jeden wpis (kto i kiedy zakończył), a pod nim pozycje historii z nazwą, znormalizowaną nazwą, kategorią, czasem i autorem odhaczenia oraz zapotrzebowaniami (zgłaszający, czas zgłoszenia, ilość, jednostka, notatka). Zakończenie bez kupionych pozycji nie tworzy wpisu.
- Teksty mówiące o „usunięciu” kupionych pozycji (potwierdzenie w UI, opis narzędzia i prompt asystenta) mówią o przeniesieniu do historii.
- Nowe tabele w bazie (migracja Alembic `0003`, wyłącznie addytywna).
- Poza zakresem: odczyt historii przez API i widok w UI (#37), nauka kolejności (#38), podpowiedzi (#39), kwoty i wydatki (świadomie pomijane).

## Capabilities

### New Capabilities

<!-- Brak — historia zakupów jest na razie tylko skutkiem zakończenia zakupów; jej odczyt (#37) może później wydzielić osobną capability. -->

### Modified Capabilities

- `shopping-list`: zakończenie zakupów przenosi kupione pozycje do historii zamiast je usuwać; nowe wymaganie opisujące, jakie dane zakupu historia zachowuje.
- `needs-chat`: scenariusz zakończenia zakupów przez czat mówi o przeniesieniu kupionych pozycji do historii po potwierdzeniu.

## Impact

- **Backend**: modele i tabele `shopping_trips`, `purchased_items`, `purchased_needs` (migracja `0003`); `kupto.lists.service.finish_shopping` zapisuje historię i usuwa kupione pozycje w jednej transakcji i przyjmuje kończącego użytkownika; narzędzia czatu `request_finish_shopping` / `confirm_finish_shopping` i prompt systemowy z nowymi opisami i nazwami pól wyniku.
- **API**: `POST /api/list/finish` bez zmian w kontrakcie (nadal zwraca listę po zakończeniu).
- **Frontend**: tylko tekst potwierdzenia „Zakończ zakupy” w `ListView`.
- **Dane produkcyjne**: migracja tylko dodaje puste tabele; istniejące dane nie są zmieniane. Pozycje usunięte przed wdrożeniem nie trafią do historii.

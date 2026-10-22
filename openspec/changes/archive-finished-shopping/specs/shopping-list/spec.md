## MODIFIED Requirements

### Requirement: Zakończenie zakupów
Członek MUST móc zakończyć zakupy: wszystkie pozycje oznaczone jako kupione MUST zostać przeniesione do historii zakupów gospodarstwa i zniknąć z aktywnej listy, a pozostałe MUST zostać bez zmian. Przeniesienie MUST być niepodzielne — kupiona pozycja nie może zniknąć z listy bez trafienia do historii ani trafić do historii, zostając na liście.

#### Scenario: Zakończenie zakupów z częścią kupionych pozycji
- **WHEN** na liście są kupione „mleko” i niekupiony „chleb”, a członek kończy zakupy
- **THEN** na liście zostaje tylko „chleb”, a „mleko” jest w historii zakupów gospodarstwa

#### Scenario: Zakończenie zakupów bez kupionych pozycji
- **WHEN** żadna pozycja na liście nie jest kupiona, a członek kończy zakupy
- **THEN** lista się nie zmienia, a w historii nie pojawia się nowe zakończenie zakupów

## ADDED Requirements

### Requirement: Historia zakupów
Każde zakończenie zakupów z co najmniej jedną kupioną pozycją MUST zostać zapisane w historii zakupów gospodarstwa jako osobne zakończenie z czasem i członkiem, który je wykonał. Każda przeniesiona pozycja MUST zachować nazwę, kategorię, czas i autora oznaczenia jako kupionej oraz wszystkie zapotrzebowania (zgłaszający, czas zgłoszenia, ilość z jednostką, notatka). Historia MUST NOT zawierać kwot ani wydatków.

#### Scenario: Zachowane dane zakupu
- **WHEN** ala zgłosiła „2 l mleka bez laktozy”, ola zgłosiła „1 l mleka”, ola oznaczyła mleko jako kupione, a ala zakończyła zakupy
- **THEN** w historii gospodarstwa jest zakończenie zakupów wykonane przez alę, a w nim pozycja „mleko” w kategorii Nabiał, kupiona przez olę w chwili odhaczenia, z zapotrzebowaniami ali (2 l, „bez laktozy”) i oli (1 l)

#### Scenario: Kolejne zakończenia zakupów
- **WHEN** członek dwukrotnie kończy zakupy z różnymi kupionymi pozycjami
- **THEN** historia zawiera dwa osobne zakończenia zakupów, każde z pozycjami kupionymi przed nim

#### Scenario: Historia jest osobna dla gospodarstwa
- **WHEN** członek innego gospodarstwa kończy zakupy
- **THEN** jego kupione pozycje trafiają wyłącznie do historii jego gospodarstwa

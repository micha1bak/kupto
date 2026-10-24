## ADDED Requirements

### Requirement: Preferencje gospodarstwa w propozycjach
Proponując dania, przepisy, składniki lub ilości, asystent MUST uwzględniać preferencje gospodarstwa: MUST NOT proponować składników wykluczonych, SHOULD unikać nielubianych, MUST dopasować propozycje do diet i czasu gotowania, a ilości do liczby osób. Gdy członek sam prosi o coś sprzecznego z preferencjami (np. wkleja przepis z wykluczonym składnikiem), asystent MUST postąpić zgodnie z prośbą i krótko wspomnieć o preferencji.

#### Scenario: Wykluczenie w propozycji
- **WHEN** gospodarstwo wyklucza orzechy, a członek prosi „zaproponuj coś słodkiego na deser”
- **THEN** propozycja nie zawiera orzechów, a lista pozostaje bez zmian

#### Scenario: Dieta w propozycji
- **WHEN** gospodarstwo ma dietę wegetariańską, a członek prosi „coś na obiad, zaproponuj zakupy”
- **THEN** zaproponowane produkty nie zawierają mięsa ani ryb

#### Scenario: Przepis sprzeczny z preferencjami
- **WHEN** gospodarstwo wyklucza orzechy, a członek wkleja przepis z orzechami
- **THEN** asystent wypisuje składniki jak przy każdym przepisie i wspomina o wykluczeniu

### Requirement: Zmiana preferencji przez czat
Asystent MUST zmieniać preferencje gospodarstwa tylko wtedy, gdy członek o to prosi albo potwierdza propozycję zapisu; MUST NOT zmieniać ich z samej wzmianki w rozmowie. Zmiana MUST zachować pozostałe preferencje i MUST NOT zmieniać listy zakupów.

#### Scenario: Prośba o zapamiętanie
- **WHEN** gospodarstwo wyklucza orzechy, a członek pisze „zapamiętaj, że Ola nie je selera”
- **THEN** wykluczenia to orzechy i seler, a lista pozostaje bez zmian

#### Scenario: Wzmianka bez prośby
- **WHEN** członek pisze „kup mleko bez laktozy, bo Ola go nie toleruje”
- **THEN** mleko trafia na listę, a preferencje gospodarstwa pozostają bez zmian

## MODIFIED Requirements

### Requirement: Dodawanie członków
Właściciel gospodarstwa MUST móc dodać innego użytkownika po jego adresie e-mail (bez względu na wielkość liter; gdy wysyłka e-maili jest dostępna — tylko po potwierdzonym adresie), a użytkownika konta bez adresu — po loginie. Dodanie MUST się nie udać, jeśli takiego użytkownika nie ma (404) albo należy już do jakiegokolwiek gospodarstwa (409). Członkowie niebędący właścicielem MUST NOT móc dodawać członków (403).

#### Scenario: Dodanie użytkownika
- **WHEN** właściciel dodaje po adresie istniejącego użytkownika bez gospodarstwa
- **THEN** użytkownik staje się członkiem i widzi wspólną listę zakupów

#### Scenario: Nieistniejący adres
- **WHEN** właściciel podaje adres, którego nie ma żadne konto
- **THEN** system zwraca 404

#### Scenario: Nieistniejący login
- **WHEN** właściciel podaje login, którego nie ma żadne konto bez adresu e-mail
- **THEN** system zwraca 404

#### Scenario: Niepotwierdzony adres
- **WHEN** wysyłka e-maili działa, a właściciel podaje adres konta, które go nie potwierdziło
- **THEN** system zwraca 404

#### Scenario: Dodawanie przez zwykłego członka
- **WHEN** członek niebędący właścicielem próbuje dodać użytkownika
- **THEN** system zwraca 403

### Requirement: Lista członków
Każdy członek gospodarstwa MUST móc pobrać listę członków z ich imionami (bez loginów i adresów e-mail) i wskazaniem właściciela.

#### Scenario: Podgląd członków
- **WHEN** członek pobiera dane gospodarstwa
- **THEN** odpowiedź zawiera nazwę gospodarstwa i wszystkich członków z imionami i oznaczeniem właściciela

## MODIFIED Requirements

### Requirement: Rejestracja konta
System MUST umożliwiać utworzenie konta na podstawie unikalnego loginu (3–50 znaków), hasła (minimum 8 znaków) i imienia (1–40 znaków po usunięciu spacji z początku i końca). Hasło MUST być przechowywane wyłącznie w postaci skrótu kryptograficznego.

#### Scenario: Udana rejestracja
- **WHEN** niezalogowany użytkownik wysyła poprawny login, hasło i imię, a login nie jest zajęty
- **THEN** system tworzy konto z tym imieniem i zwraca potwierdzenie z kodem 201

#### Scenario: Zajęty login
- **WHEN** użytkownik próbuje zarejestrować login, który już istnieje
- **THEN** system odrzuca żądanie z kodem 409 i nie tworzy konta

#### Scenario: Niepoprawne dane
- **WHEN** login lub hasło nie spełniają wymagań długości albo imienia brak, składa się z samych spacji lub jest dłuższe niż 40 znaków
- **THEN** system odrzuca żądanie z kodem 422 i opisem błędnych pól

### Requirement: Profil bieżącego użytkownika
System MUST zwracać zalogowanemu użytkownikowi jego login, imię (lub informację, że go nie podał) oraz identyfikator i nazwę gospodarstwa, do którego należy (lub informację, że nie należy do żadnego).

#### Scenario: Użytkownik w gospodarstwie
- **WHEN** zalogowany członek gospodarstwa pobiera swój profil
- **THEN** odpowiedź zawiera jego login, imię oraz identyfikator i nazwę gospodarstwa

#### Scenario: Użytkownik bez gospodarstwa
- **WHEN** zalogowany użytkownik, który nie należy do gospodarstwa, pobiera profil
- **THEN** odpowiedź zawiera jego login i imię, a pole gospodarstwa jest puste

## ADDED Requirements

### Requirement: Zmiana imienia
Zalogowany użytkownik MUST móc zmienić swoje imię (te same reguły co przy rejestracji). Imię MUST być pokazywane domownikom w czacie gospodarstwa i w powiadomieniach push o zakupach.

#### Scenario: Zmiana imienia na profilu
- **WHEN** ala zmienia imię na „Ala K.”
- **THEN** profil zwraca „Ala K.”, a jej wiadomości w czacie gospodarstwa są podpisane „Ala K.”

#### Scenario: Puste imię
- **WHEN** użytkownik wysyła imię złożone z samych spacji
- **THEN** system odrzuca żądanie z kodem 422, a imię się nie zmienia

### Requirement: Uzupełnienie imienia w istniejącym koncie
Konto utworzone przed wprowadzeniem imienia MUST po zalogowaniu zobaczyć prośbę o podanie imienia, która blokuje resztę aplikacji, dopóki imię nie zostanie zapisane. Do tego czasu wiadomości tego konta w czacie i powiadomienia push MUST być podpisane loginem.

#### Scenario: Logowanie konta bez imienia
- **WHEN** użytkownik konta bez imienia loguje się
- **THEN** widzi formularz „Jak masz na imię?”, a po jego zapisaniu przechodzi do aplikacji

#### Scenario: Konto z imieniem
- **WHEN** użytkownik z imieniem loguje się
- **THEN** nie widzi prośby o imię

# user-accounts Specification

## Purpose

Pozwala użytkownikom założyć konto i uwierzytelnić się, aby korzystać z czatu i wspólnej listy zakupów swojego gospodarstwa.

## Requirements

### Requirement: Rejestracja konta
System MUST umożliwiać utworzenie konta na podstawie unikalnego loginu (3–50 znaków) i hasła (minimum 8 znaków). Hasło MUST być przechowywane wyłącznie w postaci skrótu kryptograficznego.

#### Scenario: Udana rejestracja
- **WHEN** niezalogowany użytkownik wysyła poprawny login i hasło, a login nie jest zajęty
- **THEN** system tworzy konto i zwraca potwierdzenie z kodem 201

#### Scenario: Zajęty login
- **WHEN** użytkownik próbuje zarejestrować login, który już istnieje
- **THEN** system odrzuca żądanie z kodem 409 i nie tworzy konta

#### Scenario: Niepoprawne dane
- **WHEN** login lub hasło nie spełniają wymagań długości
- **THEN** system odrzuca żądanie z kodem 422 i opisem błędnych pól

### Requirement: Logowanie
System MUST uwierzytelniać użytkownika loginem i hasłem i po sukcesie ustanawiać sesję przechowywaną w ciasteczku niedostępnym dla JavaScriptu (httpOnly), ważną przez 30 dni.

#### Scenario: Poprawne dane logowania
- **WHEN** użytkownik podaje istniejący login i pasujące hasło
- **THEN** system ustawia ciasteczko sesji i zwraca kod 200

#### Scenario: Błędne dane logowania
- **WHEN** login nie istnieje lub hasło jest błędne
- **THEN** system zwraca kod 401 z tym samym komunikatem w obu przypadkach

### Requirement: Wylogowanie
System MUST umożliwiać zakończenie sesji przez usunięcie ciasteczka sesji.

#### Scenario: Wylogowanie zalogowanego użytkownika
- **WHEN** zalogowany użytkownik wywołuje wylogowanie
- **THEN** system usuwa ciasteczko sesji, a kolejne żądania wymagające logowania zwracają 401

### Requirement: Ochrona zasobów wymagających logowania
System MUST odrzucać kodem 401 każde żądanie do zasobów innych niż rejestracja, logowanie i sprawdzenie stanu usługi, jeśli nie zawiera ważnej sesji.

#### Scenario: Brak sesji
- **WHEN** żądanie do czatu lub listy nie zawiera ciasteczka sesji
- **THEN** system zwraca 401

#### Scenario: Wygasła lub sfałszowana sesja
- **WHEN** ciasteczko sesji jest wygasłe lub ma nieprawidłowy podpis
- **THEN** system zwraca 401

### Requirement: Profil bieżącego użytkownika
System MUST zwracać zalogowanemu użytkownikowi jego login oraz identyfikator i nazwę gospodarstwa, do którego należy (lub informację, że nie należy do żadnego).

#### Scenario: Użytkownik w gospodarstwie
- **WHEN** zalogowany członek gospodarstwa pobiera swój profil
- **THEN** odpowiedź zawiera jego login oraz identyfikator i nazwę gospodarstwa

#### Scenario: Użytkownik bez gospodarstwa
- **WHEN** zalogowany użytkownik, który nie należy do gospodarstwa, pobiera profil
- **THEN** odpowiedź zawiera jego login, a pole gospodarstwa jest puste

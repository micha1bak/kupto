## MODIFIED Requirements

### Requirement: Rejestracja konta
System MUST umożliwiać utworzenie konta na podstawie adresu e-mail (poprawnego składniowo, najwyżej 254 znaki, unikalnego bez względu na wielkość liter), hasła (minimum 8 znaków) i imienia (1–40 znaków po usunięciu spacji z początku i końca). Hasło MUST być przechowywane wyłącznie w postaci skrótu kryptograficznego. Po rejestracji system MUST wysłać na adres link weryfikacyjny, jeśli wysyłka e-maili jest dostępna.

#### Scenario: Udana rejestracja
- **WHEN** niezalogowany użytkownik wysyła poprawny adres, hasło i imię, a adres nie jest zajęty
- **THEN** system tworzy niezweryfikowane konto z tym imieniem, zwraca kod 201 i wysyła link weryfikacyjny

#### Scenario: Zajęty login
- **WHEN** użytkownik próbuje zarejestrować adres e-mail (który zastępuje login), należący już do innego konta
- **THEN** system odrzuca żądanie z kodem 409 i nie tworzy konta

#### Scenario: Zajęty adres innymi wielkościami liter
- **WHEN** istnieje konto ala@example.com, a użytkownik rejestruje Ala@Example.COM
- **THEN** system odrzuca żądanie z kodem 409 i nie tworzy konta

#### Scenario: Niepoprawne dane
- **WHEN** adres jest niepoprawny, hasło jest za krótkie albo imienia brak, składa się z samych spacji lub jest dłuższe niż 40 znaków
- **THEN** system odrzuca żądanie z kodem 422 i opisem błędnych pól

### Requirement: Logowanie
System MUST uwierzytelniać użytkownika adresem e-mail (bez względu na wielkość liter) i hasłem i po sukcesie ustanawiać sesję przechowywaną w ciasteczku niedostępnym dla JavaScriptu (httpOnly), ważną przez 30 dni. Konto bez potwierdzonego adresu utworzone przed wprowadzeniem adresów MUST móc logować się loginem, dopóki nie potwierdzi adresu; potem MUST logować się wyłącznie adresem.

#### Scenario: Poprawne dane logowania
- **WHEN** użytkownik podaje adres swojego konta (np. wielkimi literami) i pasujące hasło
- **THEN** system ustawia ciasteczko sesji i zwraca kod 200

#### Scenario: Błędne dane logowania
- **WHEN** adres nie istnieje lub hasło jest błędne
- **THEN** system zwraca kod 401 z tym samym komunikatem w obu przypadkach

#### Scenario: Logowanie loginem przed potwierdzeniem adresu
- **WHEN** użytkownik konta sprzed zmiany, bez potwierdzonego adresu, loguje się loginem i hasłem
- **THEN** system ustawia ciasteczko sesji

#### Scenario: Logowanie loginem po potwierdzeniu adresu
- **WHEN** użytkownik, który potwierdził adres, loguje się dawnym loginem
- **THEN** system zwraca 401, a logowanie adresem działa

### Requirement: Ochrona zasobów wymagających logowania
System MUST odrzucać kodem 401 każde żądanie do zasobów innych niż rejestracja, logowanie, weryfikacja adresu, reset hasła, konfiguracja logowania i sprawdzenie stanu usługi, jeśli nie zawiera ważnej sesji. Sesja wydana przed ostatnim resetem hasła konta MUST być nieważna.

#### Scenario: Brak sesji
- **WHEN** żądanie do czatu lub listy nie zawiera ciasteczka sesji
- **THEN** system zwraca 401

#### Scenario: Wygasła lub sfałszowana sesja
- **WHEN** ciasteczko sesji jest wygasłe lub ma nieprawidłowy podpis
- **THEN** system zwraca 401

#### Scenario: Sesja sprzed resetu hasła
- **WHEN** użytkownik zalogowany na telefonie resetuje hasło na komputerze
- **THEN** kolejne żądanie z telefonu zwraca 401

### Requirement: Profil bieżącego użytkownika
System MUST zwracać zalogowanemu użytkownikowi jego imię (lub informację, że go nie podał), adres e-mail ze stanem potwierdzenia (lub informację, że go nie podał), login (tylko w kontach sprzed wprowadzenia adresów), termin potwierdzenia adresu, informację, czy aplikacja jest zablokowana do potwierdzenia adresu, czy wysyłka e-maili jest dostępna, oraz identyfikator i nazwę gospodarstwa, do którego należy (lub informację, że nie należy do żadnego).

#### Scenario: Użytkownik w gospodarstwie
- **WHEN** zalogowany członek gospodarstwa pobiera swój profil
- **THEN** odpowiedź zawiera jego imię, adres ze stanem potwierdzenia oraz identyfikator i nazwę gospodarstwa

#### Scenario: Użytkownik bez gospodarstwa
- **WHEN** zalogowany użytkownik, który nie należy do gospodarstwa, pobiera profil
- **THEN** odpowiedź zawiera jego imię i adres, a pole gospodarstwa jest puste

## ADDED Requirements

### Requirement: Weryfikacja adresu e-mail
Link weryfikacyjny MUST zawierać jednorazowy token ważny 48 godzin; system MUST przechowywać wyłącznie skrót tokenu. Wystawienie nowego linku MUST unieważniać poprzednie niewykorzystane linki weryfikacyjne konta. Otwarcie ważnego linku MUST potwierdzać adres bez potrzeby logowania. Nieprawidłowy, wygasły i już użyty token MUST dawać ten sam błąd 400.

#### Scenario: Ważny link
- **WHEN** użytkownik otwiera link weryfikacyjny w ciągu 48 godzin
- **THEN** adres jest potwierdzony, a baner weryfikacji znika

#### Scenario: Wygasły link
- **WHEN** użytkownik otwiera link po 48 godzinach
- **THEN** system zwraca 400, a adres pozostaje niepotwierdzony

#### Scenario: Ponowne użycie linku
- **WHEN** ten sam link zostaje użyty drugi raz
- **THEN** system zwraca 400

#### Scenario: Ponowne wysłanie linku
- **WHEN** zalogowany użytkownik prosi o ponowne wysłanie linku
- **THEN** system wysyła nowy link, a poprzedni przestaje działać

### Requirement: Termin potwierdzenia adresu
Gdy wysyłka e-maili jest dostępna, konto z niepotwierdzonym adresem MUST mieć pełny dostęp przez 7 dni od rejestracji (lub od podania adresu w koncie sprzed zmiany) i widzieć przypomnienie z możliwością ponownego wysłania linku i zmiany adresu. Po terminie funkcje gospodarstwa MUST być niedostępne (403 z kodem `email_unverified`) do potwierdzenia adresu; profil, zmiana adresu, ponowne wysłanie linku i wylogowanie MUST działać.

#### Scenario: Konto w terminie
- **WHEN** użytkownik trzeci dzień po rejestracji bez potwierdzenia otwiera listę
- **THEN** widzi listę i baner „Potwierdź adres e-mail”

#### Scenario: Konto po terminie
- **WHEN** użytkownik osiem dni po rejestracji bez potwierdzenia otwiera aplikację
- **THEN** widzi ekran „Potwierdź adres e-mail” z ponownym wysłaniem linku, a żądania listy zwracają 403

### Requirement: Adres e-mail w istniejącym koncie
Gdy wysyłka e-maili jest dostępna, konto utworzone przed wprowadzeniem adresów MUST po zalogowaniu zobaczyć prośbę o podanie adresu, która blokuje resztę aplikacji, dopóki adres nie zostanie podany. Podany adres MUST być zapisany w koncie dopiero po potwierdzeniu linkiem; do tego czasu nie może służyć do logowania ani resetu hasła i nie blokuje adresu innym kontom.

#### Scenario: Logowanie starego konta
- **WHEN** użytkownik konta bez adresu loguje się loginem
- **THEN** widzi formularz „Podaj adres e-mail”, a po jego wysłaniu przechodzi do aplikacji z przypomnieniem o potwierdzeniu

#### Scenario: Potwierdzenie adresu starego konta
- **WHEN** użytkownik starego konta otwiera link weryfikacyjny
- **THEN** adres zostaje zapisany i potwierdzony, a od tej chwili użytkownik loguje się adresem

### Requirement: Reset hasła
System MUST umożliwiać ustawienie nowego hasła przez link wysłany na adres konta. Odpowiedź na prośbę o link MUST być taka sama bez względu na to, czy konto z tym adresem istnieje. Link MUST zawierać jednorazowy token ważny 30 minut, przechowywany wyłącznie jako skrót; nowa prośba MUST unieważniać poprzedni link. Ustawienie nowego hasła MUST zużywać token, potwierdzać adres konta i unieważniać wszystkie wcześniejsze sesje konta.

#### Scenario: Prośba o link dla istniejącego i nieistniejącego konta
- **WHEN** ktoś prosi o reset hasła dla adresu z kontem i dla adresu bez konta
- **THEN** obie odpowiedzi mają ten sam kod i treść, a mail trafia tylko do istniejącego konta

#### Scenario: Ustawienie nowego hasła
- **WHEN** użytkownik otwiera link w ciągu 30 minut i podaje nowe hasło
- **THEN** może zalogować się nowym hasłem, stare hasło przestaje działać, a wcześniejsze sesje zwracają 401

#### Scenario: Ponowne użycie linku
- **WHEN** ten sam link zostaje użyty drugi raz albo po 30 minutach
- **THEN** system zwraca 400, a hasło się nie zmienia

### Requirement: Limity prób
System MUST ograniczać liczbę rejestracji z jednego adresu IP, próśb o reset hasła (na adres i na IP) oraz wysyłek linku weryfikacyjnego (na konto i na adres) w ciągu godziny. Przekroczenie MUST dawać kod 429 z nagłówkiem `Retry-After`. Limit próśb o reset MUST działać tak samo bez względu na istnienie konta.

#### Scenario: Zbyt wiele próśb o reset
- **WHEN** ktoś czwarty raz w ciągu godziny prosi o reset hasła dla tego samego adresu
- **THEN** system zwraca 429 i nie wysyła maila

#### Scenario: Zbyt wiele rejestracji
- **WHEN** z jednego adresu IP przychodzi szósta rejestracja w ciągu godziny
- **THEN** system zwraca 429 i nie tworzy konta

### Requirement: Niedostępna wysyłka e-maili
Gdy wysyłka e-maili nie jest skonfigurowana, system MUST działać bez weryfikacji: rejestracja i logowanie działają, nikt nie jest blokowany ani proszony o adres, a prośby o reset hasła i link weryfikacyjny MUST zwracać 503 z kodem `mail_unavailable`, jednakowo dla wszystkich adresów. Aplikacja MUST informować o tym na stronie „Zapomniałem hasła”.

#### Scenario: Reset hasła bez wysyłki
- **WHEN** wysyłka jest niedostępna, a użytkownik otwiera „Zapomniałem hasła”
- **THEN** widzi komunikat, że wysyłka e-maili jest chwilowo niedostępna

#### Scenario: Stare konto bez wysyłki
- **WHEN** wysyłka jest niedostępna, a użytkownik konta bez adresu loguje się loginem
- **THEN** przechodzi do aplikacji bez prośby o adres

### Requirement: Dane konta niewidoczne dla domowników
Odpowiedzi pokazujące innych użytkowników (lista, historia, przepisy, plan obiadów, preferencje, domownicy) MUST zawierać ich imię, a nie login ani adres e-mail. Linki i tokeny z maili MUST NOT trafiać do logów aplikacji poza jawnie włączonym trybem deweloperskim.

#### Scenario: Zapotrzebowanie domownika
- **WHEN** Ala (konto ala@example.com) dodaje mleko, a Ola pobiera listę
- **THEN** przy zapotrzebowaniu widnieje „Ala”, a odpowiedź nie zawiera adresu ani loginu Ali

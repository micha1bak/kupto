## MODIFIED Requirements

### Requirement: Widoczność zmian innych członków
Zmiany listy wprowadzone przez jednego członka (przez czat lub ręcznie) MUST być widoczne dla pozostałych członków z otwartą aplikacją bez ręcznego odświeżania strony: przy działającym połączeniu na żywo w ciągu kilku sekund, a gdy połączenie na żywo jest niedostępne — najpóźniej po 30 sekundach. Po powrocie do aplikacji (karta lub aplikacja ponownie na pierwszym planie) lista MUST zostać odświeżona od razu.

#### Scenario: Zmiana przez innego członka
- **WHEN** członek A dodaje pozycję, a członek B ma otwarty widok listy z działającym połączeniem na żywo
- **THEN** pozycja pojawia się u członka B w ciągu kilku sekund

#### Scenario: Zmiana przez czat
- **WHEN** członek A prosi asystenta czatu o dodanie pozycji, a członek B ma otwarty widok listy
- **THEN** pozycja pojawia się u członka B bez ręcznego odświeżania

#### Scenario: Połączenie na żywo niedostępne
- **WHEN** połączenie na żywo członka B nie działa, a członek A zmienia listę
- **THEN** zmiana pojawia się u członka B najpóźniej po 30 sekundach

#### Scenario: Powrót do aplikacji
- **WHEN** członek B wraca do karty z aplikacją, a w tym czasie lista się zmieniła
- **THEN** lista u członka B jest odświeżana od razu po powrocie

## ADDED Requirements

### Requirement: Strumień zmian listy
System MUST udostępniać zalogowanemu członkowi gospodarstwa strumień zdarzeń (SSE) sygnalizujących zmianę listy jego gospodarstwa, bez treści listy. Brak sesji MUST skutkować 401, brak gospodarstwa — 409. Członek MUST NOT otrzymywać zdarzeń o zmianach list innych gospodarstw; po opuszczeniu lub usunięciu z gospodarstwa jego strumień MUST się zakończyć.

#### Scenario: Zmiana listy własnego gospodarstwa
- **WHEN** członek ma otwarty strumień, a inny członek jego gospodarstwa odhacza pozycję
- **THEN** strumień dostarcza zdarzenie zmiany listy

#### Scenario: Zmiana listy innego gospodarstwa
- **WHEN** członek ma otwarty strumień, a użytkownik innego gospodarstwa dodaje pozycję na swoją listę
- **THEN** strumień nie dostarcza zdarzenia zmiany listy

#### Scenario: Użytkownik bez gospodarstwa
- **WHEN** zalogowany użytkownik bez gospodarstwa otwiera strumień
- **THEN** system zwraca 409

#### Scenario: Usunięcie z gospodarstwa
- **WHEN** właściciel usuwa członka, który ma otwarty strumień
- **THEN** strumień tego członka się kończy

#### Scenario: Zmiana własnej kolejności kategorii
- **WHEN** członek ma otwarty strumień na dwóch urządzeniach i przypina kategorię na jednym z nich
- **THEN** strumień na drugim urządzeniu dostarcza zdarzenie zmiany listy, a strumienie pozostałych członków nie

### Requirement: Podtrzymanie strumienia zmian
Otwarty strumień zmian listy MUST wysyłać sygnał podtrzymania co najwyżej co 30 sekund, także gdy lista się nie zmienia, żeby pośrednicy sieciowi nie zamykali bezczynnego połączenia. Po zerwaniu połączenia klient MUST łączyć się ponownie i MUST pobrać aktualną listę, bo zmiany z czasu rozłączenia nie są dostarczane ponownie.

#### Scenario: Bezczynna lista
- **WHEN** strumień jest otwarty, a lista nie zmienia się przez dłuższy czas
- **THEN** strumień co najwyżej co 30 sekund wysyła sygnał podtrzymania

#### Scenario: Ponowne połączenie
- **WHEN** połączenie strumienia zostało zerwane, a w tym czasie lista się zmieniła
- **THEN** klient łączy się ponownie i pobiera aktualną listę

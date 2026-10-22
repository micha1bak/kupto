## Purpose

Powiadomienia push na urządzenia członków gospodarstwa: włączanie i wyłączanie na urządzeniu, przechowywanie subskrypcji, dostarczanie i wygląd powiadomień oraz działanie aplikacji bez skonfigurowanych kluczy. Konkretne powiadomienia (np. o zakupach) korzystają z tej infrastruktury.

## ADDED Requirements

### Requirement: Działanie bez kluczy serwera
Powiadomienia MUST być wyłączone, gdy serwer nie ma kompletnej i poprawnej konfiguracji kluczy VAPID; reszta aplikacji MUST wtedy działać bez zmian. Przy wyłączonych powiadomieniach publiczny klucz MUST NOT być udostępniany, a próba wysyłki MUST być pomijana bez błędu.

#### Scenario: Brak kluczy
- **WHEN** serwer działa bez kluczy VAPID, a zalogowany użytkownik pyta o publiczny klucz
- **THEN** dostaje odpowiedź 404 z kodem `push_disabled`, a lista i czat działają normalnie

#### Scenario: Wysyłka przy wyłączonych powiadomieniach
- **WHEN** aplikacja próbuje wysłać powiadomienie bez skonfigurowanych kluczy
- **THEN** nic nie jest wysyłane i żadne żądanie nie kończy się błędem

### Requirement: Subskrypcje urządzeń
Zalogowany użytkownik MUST móc zapisać subskrypcję push swojego urządzenia i ją usunąć. Użytkownik MAY mieć kilka urządzeń. Subskrypcja (identyfikowana adresem usługi push) MUST należeć do najwyżej jednego użytkownika — ponowny zapis tej samej subskrypcji aktualizuje ją i przypisuje do zalogowanego użytkownika. Użytkownik MUST NOT móc usunąć cudzej subskrypcji. Adres usługi push MUST być adresem HTTPS znanej usługi push przeglądarek. Operacje na subskrypcjach MUST wymagać zalogowania.

#### Scenario: Dwa urządzenia
- **WHEN** ala zapisuje subskrypcję telefonu i laptopa
- **THEN** powiadomienia do ali trafiają na oba urządzenia

#### Scenario: Zmiana konta na urządzeniu
- **WHEN** ola loguje się na urządzeniu, którego subskrypcja należała do ali, i zapisuje ją ponownie
- **THEN** subskrypcja należy do oli, a ala nie dostaje już na to urządzenie powiadomień

#### Scenario: Cudza subskrypcja
- **WHEN** ola próbuje usunąć subskrypcję urządzenia ali
- **THEN** subskrypcja ali zostaje bez zmian

#### Scenario: Bez logowania
- **WHEN** niezalogowany klient zapisuje lub usuwa subskrypcję albo pyta o klucz
- **THEN** dostaje odpowiedź 401

#### Scenario: Niedozwolony adres
- **WHEN** klient zapisuje subskrypcję z adresem spoza znanych usług push albo bez HTTPS
- **THEN** dostaje odpowiedź 422 i nic nie jest zapisywane

### Requirement: Dostarczanie powiadomień
Powiadomienie MUST być wysyłane po zapisaniu zmiany, która je wywołała, i MUST NOT opóźniać ani psuć odpowiedzi na żądanie użytkownika. Każde powiadomienie MUST mieć typ, określony czas ważności i pilność. Gdy usługa push odpowie, że subskrypcja nie istnieje lub wygasła (404 lub 410), subskrypcja MUST zostać usunięta. Błąd lub brak odpowiedzi jednej usługi push MUST NOT wstrzymywać wysyłki na inne urządzenia.

#### Scenario: Wygasła subskrypcja
- **WHEN** usługa push odpowiada 410 na powiadomienie do jednego z urządzeń ali
- **THEN** ta subskrypcja zostaje usunięta, a pozostałe urządzenia ali dostają powiadomienie

#### Scenario: Usługa push nie odpowiada
- **WHEN** usługa push jednego urządzenia nie odpowiada w wyznaczonym czasie
- **THEN** wysyłka na to urządzenie zostaje przerwana, subskrypcja zostaje, a odpowiedź na żądanie użytkownika nie czekała na wysyłkę

#### Scenario: Powiadomienie do gospodarstwa
- **WHEN** aplikacja wysyła powiadomienie do gospodarstwa z pominięciem autora zmiany
- **THEN** dostają je wszystkie zapisane urządzenia pozostałych członków tego gospodarstwa i żadne urządzenie spoza niego

### Requirement: Wyświetlenie i kliknięcie powiadomienia
Urządzenie MUST wyświetlić otrzymane powiadomienie z tytułem i treścią; powiadomienia z tym samym tagiem MUST zastępować się nawzajem zamiast mnożyć. Kliknięcie powiadomienia MUST przenieść użytkownika do otwartej karty aplikacji, a gdy żadna nie jest otwarta — otworzyć adres wskazany w powiadomieniu (domyślnie stronę główną).

#### Scenario: Grupowanie
- **WHEN** urządzenie dostaje dwa powiadomienia z tym samym tagiem
- **THEN** widoczne jest tylko nowsze

#### Scenario: Kliknięcie przy zamkniętej aplikacji
- **WHEN** użytkownik klika powiadomienie, a aplikacja nie jest otwarta
- **THEN** otwiera się aplikacja pod adresem z powiadomienia

### Requirement: Włączanie powiadomień na urządzeniu
Aplikacja MUST pytać przeglądarkę o zgodę na powiadomienia wyłącznie po kliknięciu „Włącz powiadomienia”, nigdy przy starcie. Wylogowanie MUST wyłączać powiadomienia na tym urządzeniu.

#### Scenario: Włączenie
- **WHEN** użytkownik z wyłączonymi powiadomieniami klika „Włącz powiadomienia” i zgadza się w oknie przeglądarki
- **THEN** subskrypcja urządzenia zostaje zapisana, a stan zmienia się na „włączone”

#### Scenario: Brak pytania przy starcie
- **WHEN** użytkownik otwiera aplikację
- **THEN** przeglądarka nie pyta o zgodę na powiadomienia

#### Scenario: Wyłączenie
- **WHEN** użytkownik z włączonymi powiadomieniami klika „Wyłącz powiadomienia”
- **THEN** subskrypcja urządzenia zostaje usunięta, a stan zmienia się na „wyłączone”

#### Scenario: Wylogowanie
- **WHEN** użytkownik z włączonymi powiadomieniami wylogowuje się
- **THEN** urządzenie przestaje dostawać jego powiadomienia

### Requirement: Stan powiadomień na urządzeniu
Aplikacja MUST pokazywać stan powiadomień na tym urządzeniu: włączone, wyłączone, zablokowane w przeglądarce (z informacją, jak odblokować), nieobsługiwane przez przeglądarkę albo niedostępne na serwerze. Na iPhonie i iPadzie bez aplikacji dodanej do ekranu początkowego MUST pokazywać informację, że powiadomienia wymagają instalacji.

#### Scenario: Odmowa zgody
- **WHEN** użytkownik odmawia zgody w oknie przeglądarki
- **THEN** stan to „zablokowane” z informacją, jak zmienić to w ustawieniach przeglądarki

#### Scenario: iPhone w Safari
- **WHEN** użytkownik otwiera aplikację w Safari na iPhonie, bez dodania do ekranu początkowego
- **THEN** zamiast przycisku widzi informację, że powiadomienia działają po dodaniu Kupto do ekranu początkowego

#### Scenario: Serwer bez kluczy
- **WHEN** serwer ma wyłączone powiadomienia
- **THEN** aplikacja informuje, że powiadomienia są niedostępne, i nie pokazuje przycisku włączenia

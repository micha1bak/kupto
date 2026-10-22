## ADDED Requirements

### Requirement: Ustawienia typów powiadomień
Zalogowany użytkownik MUST móc włączyć lub wyłączyć osobno każdy typ powiadomień: rozpoczęcie zakupów, dopisanie w trakcie zakupów i zakończenie zakupów. Ustawienia MUST dotyczyć użytkownika (wszystkich jego urządzeń), a nie pojedynczego urządzenia, i MUST być niezależne od włączenia powiadomień na urządzeniu. Typ, którego użytkownik nie zmieniał, MUST mieć wartość domyślną; dla obecnych typów domyślnie jest włączony.

#### Scenario: Domyślnie wszystko włączone
- **WHEN** ala, która nie zmieniała ustawień, otwiera ustawienia powiadomień
- **THEN** wszystkie trzy typy są włączone

#### Scenario: Wyłączenie typu
- **WHEN** ala wyłącza powiadomienia o rozpoczęciu zakupów
- **THEN** ten typ jest u niej wyłączony, a pozostałe typy i ustawienia oli są bez zmian

#### Scenario: Ustawienia na innym urządzeniu
- **WHEN** ala wyłącza typ na telefonie, a potem otwiera ustawienia na laptopie
- **THEN** na laptopie ten typ też jest wyłączony

### Requirement: Dostęp do ustawień powiadomień
Użytkownik MUST widzieć i zmieniać tylko własne ustawienia powiadomień, a operacje na nich MUST wymagać zalogowania. Ustawienia MUST być dostępne także wtedy, gdy powiadomienia są wyłączone na serwerze. Zmiana ustawienia nieistniejącego typu MUST być odrzucana.

#### Scenario: Nieznany typ
- **WHEN** klient próbuje zmienić ustawienie typu, którego nie ma
- **THEN** dostaje odpowiedź 422 i nic nie jest zapisywane

#### Scenario: Bez logowania
- **WHEN** niezalogowany klient odczytuje lub zmienia ustawienia
- **THEN** dostaje odpowiedź 401

### Requirement: Wysyłka zgodna z ustawieniami
Powiadomienie danego typu MUST NOT trafić na żadne urządzenie użytkownika, który wyłączył ten typ — zarówno przy wysyłce do gospodarstwa, jak i do wskazanych użytkowników. Pozostali adresaci MUST dostać powiadomienie jak dotąd. Zmiana ustawień MUST obowiązywać od następnego wysyłanego powiadomienia.

#### Scenario: Wyłączony typ przy wysyłce do gospodarstwa
- **WHEN** ola wyłączyła powiadomienia o rozpoczęciu zakupów, a ala zaczyna zakupy
- **THEN** ewa dostaje „ala idzie na zakupy”, a żadne urządzenie oli nie

#### Scenario: Inny typ nadal przychodzi
- **WHEN** ola wyłączyła tylko powiadomienia o rozpoczęciu zakupów, a ala kończy zakupy
- **THEN** ola dostaje powiadomienie o zakończeniu zakupów

#### Scenario: Wyłączony typ przy wysyłce do kupujących
- **WHEN** ala robi zakupy z wyłączonymi powiadomieniami o dopisaniu w trakcie, a ola dopisuje produkt
- **THEN** ala nie dostaje powiadomienia o dopisaniu

#### Scenario: Ponowne włączenie
- **WHEN** ola włącza z powrotem powiadomienia o rozpoczęciu zakupów, a ala znowu zaczyna zakupy
- **THEN** ola dostaje powiadomienie

### Requirement: Przełączniki typów w aplikacji
Na karcie powiadomień, gdy powiadomienia są dostępne na serwerze i w przeglądarce, aplikacja MUST pokazywać przełącznik dla każdego typu powiadomień z krótkim opisem i bieżącym stanem użytkownika. Zmiana przełącznika MUST być zapisywana od razu; gdy zapis się nie uda, przełącznik MUST wrócić do poprzedniego stanu z komunikatem o błędzie.

#### Scenario: Zmiana przełącznika
- **WHEN** ala odznacza „Ktoś idzie na zakupy”
- **THEN** ustawienie zostaje zapisane, a przełącznik pozostaje odznaczony

#### Scenario: Błąd zapisu
- **WHEN** zapis ustawienia się nie udaje
- **THEN** przełącznik wraca do poprzedniego stanu i widać komunikat o błędzie

#### Scenario: Powiadomienia niedostępne
- **WHEN** serwer ma wyłączone powiadomienia
- **THEN** przełączniki typów nie są pokazywane

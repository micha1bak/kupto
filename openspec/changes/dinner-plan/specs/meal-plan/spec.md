## ADDED Requirements

### Requirement: Plan obiadów gospodarstwa
Gospodarstwo MUST mieć plan obiadów: najwyżej jedno danie na dzień, z nazwą dania i opcjonalnym odwołaniem do przepisu gospodarstwa. Plan MUST być wspólny dla gospodarstwa: każdy członek MUST móc go odczytać i zmieniać; inne gospodarstwa MUST NOT mieć do niego dostępu. Ustawienie dania na dzień MUST zastąpić poprzednie danie tego dnia. Po usunięciu przepisu danie MUST pozostać w planie pod swoją nazwą, bez odwołania do przepisu.

#### Scenario: Ustawienie dania na dzień
- **WHEN** ala ustawia na 27 października danie z przepisu „Naleśniki” bez podawania nazwy
- **THEN** ola z tego samego gospodarstwa widzi 27 października „Naleśniki” z odwołaniem do przepisu i z informacją, że zaplanowała je ala

#### Scenario: Zmiana dania
- **WHEN** na 27 października są „Naleśniki”, a ola ustawia na ten dzień „Pierogi”
- **THEN** 27 października jest tylko „Pierogi”

#### Scenario: Usunięty przepis
- **WHEN** w planie są „Naleśniki” z przepisu, a przepis zostaje usunięty
- **THEN** w planie nadal są „Naleśniki”, bez odwołania do przepisu

#### Scenario: Przepis innego gospodarstwa
- **WHEN** ala ustawia danie z przepisem gospodarstwa ewy
- **THEN** system odpowiada kodem 404, a plan pozostaje bez zmian

#### Scenario: Izolacja gospodarstw
- **WHEN** ewa z innego gospodarstwa odczytuje plan na tydzień, w którym ala zaplanowała obiady
- **THEN** ewa nie widzi żadnych dań gospodarstwa ali

### Requirement: Odczyt i edycja planu po dniach
System MUST udostępniać plan z zakresu dat (włącznie, rosnąco po dniu, bez dni bez obiadu) dla zakresu do 62 dni oraz usunięcie dania z wybranego dnia — tak, by kalendarz posiłków mógł pokazać i edytować tydzień.

#### Scenario: Odczyt tygodnia
- **WHEN** gospodarstwo ma obiady na 26 i 28 października oraz 3 listopada, a członek odczytuje plan od 26 października do 1 listopada
- **THEN** system zwraca dania z 26 i 28 października, w tej kolejności

#### Scenario: Zbyt długi zakres
- **WHEN** członek odczytuje plan z zakresu dłuższego niż 62 dni albo z datą początku po dacie końca
- **THEN** system odpowiada kodem 400

#### Scenario: Usunięcie dnia
- **WHEN** członek usuwa obiad z 28 października
- **THEN** 28 października nie ma dania, a pozostałe dni planu są bez zmian

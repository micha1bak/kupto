## ADDED Requirements

### Requirement: Kalendarz posiłków w aplikacji
Aplikacja MUST pokazywać plan obiadów gospodarstwa jako kalendarz: bieżący i następny tydzień (od poniedziałku) jako pionową listę dni, z przejściem o tydzień wstecz i w przód. Dzień z daniem MUST pokazywać nazwę dania, a gdy danie ma przepis gospodarstwa — link do przepisu. Po wymianie w czacie kalendarz MUST pokazywać aktualny plan. Widok MUST mieścić się w szerokości 375 px bez przewijania w poziomie.

#### Scenario: Podgląd dwóch tygodni
- **WHEN** we wtorek 27 października ala otwiera plan obiadów, a na 28 października są zaplanowane „Naleśniki” z przepisu
- **THEN** widzi dni od 26 października do 8 listopada, przy 28 października „Naleśniki” z linkiem do przepisu, a pozostałe dni bez dania z możliwością dodania

#### Scenario: Następny tydzień
- **WHEN** ala przechodzi o tydzień dalej
- **THEN** widzi dni od 2 do 15 listopada z daniami zapisanymi na te dni

#### Scenario: Plan zapisany przez czat
- **WHEN** asystent zapisał w czacie plan obiadów, a ala ma otwarty kalendarz
- **THEN** po zakończeniu wymiany kalendarz pokazuje zapisane dania

### Requirement: Edycja planu w kalendarzu
Członek MUST móc w kalendarzu dodać i zmienić danie dnia, podając nazwę albo wybierając przepis gospodarstwa, oraz usunąć danie po potwierdzeniu. Z dnia, którego danie ma przepis, członek MUST móc dodać na listę zaznaczone brakujące składniki tak samo jak ze strony przepisu.

#### Scenario: Danie z przepisu
- **WHEN** ala dodaje na 29 października danie, wybierając przepis „Pierogi”
- **THEN** w planie 29 października są „Pierogi” z odwołaniem do przepisu

#### Scenario: Zmiana na własną nazwę
- **WHEN** ala zmienia danie 28 października na „Zupa pomidorowa” bez przepisu
- **THEN** 28 października jest „Zupa pomidorowa” bez linku do przepisu

#### Scenario: Usunięcie z potwierdzeniem
- **WHEN** ala wybiera usunięcie dania z 28 października i potwierdza
- **THEN** 28 października nie ma dania; bez potwierdzenia plan pozostaje bez zmian

#### Scenario: Brakujące składniki z dnia
- **WHEN** przy „Naleśnikach” z przepisu ala wybiera „Dodaj brakujące składniki”, zaznacza mleko i dodaje
- **THEN** na liście pojawia się jej zapotrzebowanie na mleko z notatką „na: Naleśniki”, a aplikacja pokazuje komunikat z dodanymi produktami

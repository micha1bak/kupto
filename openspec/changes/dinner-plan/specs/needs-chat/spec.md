## ADDED Requirements

### Requirement: Plan obiadów przez czat
Na prośbę o plan obiadów na kilka dni asystent MUST zaproponować po jednym daniu na każdy dzień, z datami, z przepisów gospodarstwa i/lub nowych dań, zgodnie z preferencjami gospodarstwa. Przed potwierdzeniem MUST NOT zapisywać planu ani zmieniać listy. Po potwierdzeniu (także z poprawkami) MUST zapisać plan, a dania z przepisów z odwołaniem do przepisu. Na pytanie o plan MUST odpowiedzieć na podstawie zapisanego planu.

#### Scenario: Propozycja planu bez zapisu
- **WHEN** członek pisze „zaplanuj obiady na 3 dni od jutra”
- **THEN** asystent proponuje trzy dania z datami, a plan i lista pozostają bez zmian

#### Scenario: Zapis po potwierdzeniu z poprawką
- **WHEN** po propozycji planu członek odpowiada „tak, ale w drugi dzień zrób naleśniki”
- **THEN** w planie gospodarstwa są trzy kolejne dni, drugiego dnia naleśniki (z odwołaniem do przepisu „Naleśniki”, gdy gospodarstwo go ma)

#### Scenario: Pytanie o plan
- **WHEN** gospodarstwo ma na jutro zaplanowane „Pierogi”, a członek pyta „co jutro na obiad?”
- **THEN** asystent odpowiada, że pierogi, i nie zmienia planu ani listy

### Requirement: Składniki z planu obiadów na listę
Po zapisie planu asystent MUST wypisać składniki zaplanowanych dań i zapytać, czego brakuje, nie zmieniając listy. Po odpowiedzi MUST dodać tylko brakujące składniki jako zapotrzebowania autora z notatką „na: <danie>”.

#### Scenario: Pytanie o brakujące po zapisie
- **WHEN** asystent zapisał plan po potwierdzeniu
- **THEN** w tej samej odpowiedzi wymienia składniki dań i pyta, czego brakuje, a lista pozostaje bez zmian

#### Scenario: Brakujące składniki z planu
- **WHEN** po zapisie planu i pytaniu o składniki członek odpowiada „brakuje tylko mleka”
- **THEN** na liście pojawia się zapotrzebowanie członka na mleko z notatką „na: <danie>” wskazującą danie z planu, bez pozostałych składników

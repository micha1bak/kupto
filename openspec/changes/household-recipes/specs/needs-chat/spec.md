## ADDED Requirements

### Requirement: Zapis przepisu przez czat
Asystent MUST zapisać przepis omawiany w rozmowie (wklejony albo z linku) w bazie przepisów gospodarstwa tylko wtedy, gdy członek o to prosi albo potwierdza propozycję zapisu; MUST NOT zapisywać przepisów z własnej inicjatywy. Zapis MUST obejmować wszystkie składniki przepisu (także wodę, sól i pieprz) i MUST NOT zmieniać listy zakupów. Gdy nazwa jest zajęta, asystent MUST o tym powiedzieć.

#### Scenario: Zapis przepisu z rozmowy
- **WHEN** członek wkleja przepis na naleśniki, a potem pisze „zapisz ten przepis”
- **THEN** w przepisach gospodarstwa jest przepis o nazwie naleśników ze składnikami z przepisu, a lista zakupów pozostaje bez zmian

#### Scenario: Bez prośby nie ma zapisu
- **WHEN** członek wkleja przepis bez prośby o zapisanie
- **THEN** w przepisach gospodarstwa nic nie przybywa

### Requirement: Lista z zapisanego przepisu przez czat
Na prośbę o zakupy do zapisanego przepisu asystent MUST odczytać przepis z bazy gospodarstwa i postąpić jak przy wklejonym przepisie: wypisać składniki, zapytać, czego brakuje, i dopiero po odpowiedzi dodać tylko brakujące z notatką „na: <danie>”.

#### Scenario: Zakupy do zapisanego przepisu
- **WHEN** gospodarstwo ma zapisany przepis „Naleśniki”, a członek pisze „chcę zrobić naleśniki z naszych przepisów”
- **THEN** asystent wymienia składniki zapisanego przepisu i pyta, czego brakuje, a lista pozostaje bez zmian

#### Scenario: Potwierdzenie brakujących składników zapisanego przepisu
- **WHEN** po propozycji składników zapisanego przepisu członek odpowiada „brakuje tylko mleka”
- **THEN** na liście pojawia się zapotrzebowanie członka na mleko z notatką „na: naleśniki”, bez pozostałych składników

## ADDED Requirements

### Requirement: Preferencje gospodarstwa
Gospodarstwo MUST mieć jeden wspólny zestaw preferencji: liczbę osób, diety, wykluczenia (alergie i produkty, których domownicy nie jedzą), nielubiane składniki, maksymalny czas gotowania i krótkie inne uwagi. Każde pole MUST być opcjonalne, a gospodarstwo bez zapisanych preferencji MUST NOT mieć żadnych. Każdy członek MUST móc preferencje odczytać i zmienić; zapis MUST zastępować całość i zapamiętywać, kto i kiedy zmienił. Inne gospodarstwa MUST NOT mieć do nich dostępu.

#### Scenario: Brak preferencji
- **WHEN** członek gospodarstwa, które nie zapisało preferencji, je odczytuje
- **THEN** wszystkie pola są puste

#### Scenario: Zapis przez członka
- **WHEN** ola (nie właściciel) zapisuje 4 osoby, dietę „wegetariańska” i wykluczenie „orzechy”
- **THEN** ala z tego samego gospodarstwa widzi te preferencje i to, że zmieniła je ola

#### Scenario: Izolacja gospodarstw
- **WHEN** ewa z innego gospodarstwa odczytuje preferencje
- **THEN** widzi preferencje swojego gospodarstwa, a nie gospodarstwa ali

#### Scenario: Porządkowanie list
- **WHEN** członek zapisuje wykluczenia „ orzechy”, „Orzechy” i „”
- **THEN** zapisane jest jedno wykluczenie „orzechy”

#### Scenario: Wartość spoza zakresu
- **WHEN** członek zapisuje liczbę osób 0
- **THEN** system odrzuca zapis z kodem 422, a preferencje pozostają bez zmian

### Requirement: Preferencje w aplikacji
Strona gospodarstwa MUST mieć sekcję „Preferencje” z formularzem wszystkich pól i zapisem; listy MUST dać się wpisać jako pozycje oddzielone przecinkami. Po zapisie członek MUST zobaczyć potwierdzenie, a po zmianie preferencji przez czat sekcja MUST pokazać nowe wartości.

#### Scenario: Zapis w UI
- **WHEN** ala wpisuje w wykluczeniach „orzechy, seler” i wybiera „Zapisz preferencje”
- **THEN** zapisane są dwa wykluczenia, a aplikacja pokazuje „Zapisano”

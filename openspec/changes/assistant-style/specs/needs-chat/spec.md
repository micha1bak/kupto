## ADDED Requirements

### Requirement: Odpowiedź po wykonanej akcji
Po zmianie listy, statusu zakupów, przepisów, preferencji lub planu obiadów asystent MUST krótko napisać, co zrobił, i MUST NOT kończyć odpowiedzi pytaniem zamykającym ani ofertą dalszej pomocy (np. „Czy potrzebujesz czegoś jeszcze?”). Pytania MUST pozostać tam, gdzie są potrzebne: potwierdzenie przed akcją wymagającą zgody (propozycja przy ogólnej potrzebie, składniki przepisu, plan obiadów, zakończenie zakupów) oraz pytanie, bez odpowiedzi na które nie da się wykonać prośby.

#### Scenario: Dodanie produktów
- **WHEN** członek pisze „kup 2 mleka, chleb i płyn do naczyń”
- **THEN** odpowiedź wymienia dodane pozycje i nie kończy się pytaniem

#### Scenario: Oznaczenie kupionego
- **WHEN** członek pisze „kupiłem mleko i chleb”
- **THEN** odpowiedź mówi, co oznaczono jako kupione, i nie kończy się pytaniem

#### Scenario: Potwierdzone zakończenie zakupów
- **WHEN** członek potwierdza zakończenie zakupów
- **THEN** odpowiedź mówi, że kupione pozycje przeniesiono do historii, i nie kończy się pytaniem

#### Scenario: Pytanie potwierdzające zostaje
- **WHEN** członek pisze „skończyłem zakupy” albo „potrzebujemy czegoś na grilla”
- **THEN** asystent pyta o potwierdzenie, a lista pozostaje bez zmian

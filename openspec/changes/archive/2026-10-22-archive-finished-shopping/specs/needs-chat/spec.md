## MODIFIED Requirements

### Requirement: Inne operacje na liście przez czat
Asystent MUST umożliwiać w rozmowie: sprawdzenie zawartości listy, zmianę ilości i wycofanie własnych zapotrzebowań, usunięcie pozycji oraz oznaczenie pozycji jako kupionej. Zakończenie zakupów przez czat MUST wymagać wyraźnego potwierdzenia w rozmowie.

#### Scenario: Pytanie o listę
- **WHEN** członek pyta „co mamy na liście?”
- **THEN** asystent odpowiada aktualną zawartością listy gospodarstwa

#### Scenario: Oznaczenie kupionego
- **WHEN** członek pisze „kupiłem mleko i chleb”
- **THEN** obie pozycje zostają oznaczone jako kupione przez tego członka

#### Scenario: Zakończenie zakupów przez czat
- **WHEN** członek pisze „skończyłem zakupy”
- **THEN** asystent prosi o potwierdzenie i przenosi kupione pozycje z listy do historii zakupów dopiero po jego otrzymaniu

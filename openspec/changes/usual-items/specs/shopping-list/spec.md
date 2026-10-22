## ADDED Requirements

### Requirement: Podpowiedzi zwykle kupowanych produktów
System MUST podpowiadać członkowi produkty, które jego gospodarstwo kupuje regularnie, a których nie ma teraz na liście: kupione w co najmniej 3 zakończeniach zakupów z ostatniego roku, gdy od ostatniego zakupu minęło od 0,8 do 3 typowych odstępów (mediana odstępów, co najmniej 1 dzień). Podpowiedź MUST zawierać typową ilość, jeśli była podawana, i MUST pochodzić wyłącznie z historii gospodarstwa członka.

#### Scenario: Zwykły produkt, którego brakuje
- **WHEN** gospodarstwo kupowało mleko (2 l) co tydzień w czterech zakończeniach, ostatnio tydzień temu, a mleka nie ma na liście
- **THEN** podpowiedzi zawierają mleko z typową ilością 2 l

#### Scenario: Produkt już na liście
- **WHEN** gospodarstwo kupuje mleko co tydzień, ostatnio tydzień temu, a mleko jest na liście
- **THEN** podpowiedzi nie zawierają mleka

#### Scenario: Jeszcze za wcześnie
- **WHEN** gospodarstwo kupuje mleko co tydzień, a ostatnio kupiło je wczoraj
- **THEN** podpowiedzi nie zawierają mleka

#### Scenario: Produkt porzucony
- **WHEN** gospodarstwo kupowało mleko co tydzień, ale ostatnio dwa miesiące temu
- **THEN** podpowiedzi nie zawierają mleka

#### Scenario: Zimny start
- **WHEN** gospodarstwo kupiło mleko tylko w dwóch zakończeniach zakupów
- **THEN** podpowiedzi nie zawierają mleka

#### Scenario: Historia innego gospodarstwa
- **WHEN** inne gospodarstwo regularnie kupuje kawę, a gospodarstwo ali nigdy jej nie kupowało
- **THEN** podpowiedzi ali nie zawierają kawy

### Requirement: Podpowiedzi przy liście
Członek MUST móc dodać podpowiedziany produkt jednym kliknięciem jako zwykłe zapotrzebowanie z typową ilością i MUST móc ukryć podpowiedzi na danym urządzeniu do końca dnia.

#### Scenario: Dodanie jednym kliknięciem
- **WHEN** ala klika podpowiedziane mleko z typową ilością 2 l
- **THEN** na liście pojawia się zapotrzebowanie ali na 2 l mleka w kategorii Nabiał, a mleko znika z podpowiedzi

#### Scenario: Ukrycie na dziś
- **WHEN** ala ukrywa podpowiedzi
- **THEN** podpowiedzi nie są pokazywane na tym urządzeniu do końca dnia

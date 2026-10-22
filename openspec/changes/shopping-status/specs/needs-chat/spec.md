## ADDED Requirements

### Requirement: Status zakupów przez czat
Asystent MUST włączać status zakupów autora wiadomości, gdy ten pisze, że idzie do sklepu lub jest w sklepie, i MUST go wyłączać, gdy autor pisze, że skończył zakupy albo jednak nie idzie. Zmiana statusu MUST NOT zmieniać pozycji na liście. Asystent MUST umieć odpowiedzieć, kto z gospodarstwa robi teraz zakupy.

#### Scenario: Idę do sklepu
- **WHEN** ala pisze „idę do sklepu”
- **THEN** ala ma aktywny status zakupów, a pozycje listy się nie zmieniają

#### Scenario: Skończyłem zakupy
- **WHEN** ala z aktywnym statusem pisze „skończyłem zakupy”
- **THEN** status ali zostaje wyłączony, a przeniesienie kupionych pozycji do historii nadal wymaga potwierdzenia

#### Scenario: Pytanie, kto jest w sklepie
- **WHEN** ola ma aktywny status, a ala pyta „czy ktoś jest w sklepie?”
- **THEN** asystent odpowiada, że zakupy robi ola

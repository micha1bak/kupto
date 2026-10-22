## ADDED Requirements

### Requirement: Podpowiedzi zwykłych produktów w czacie
Na pytania o produkty kupowane zwykle (np. „czego nam zwykle brakuje?”, „co zwykle kupujemy?”) asystent MUST zaproponować produkty, które gospodarstwo kupuje regularnie, a których nie ma na liście (wg tej samej reguły co podpowiedzi przy liście), z typową ilością, i MUST NOT zmieniać listy, dopóki członek ich nie potwierdzi lub nie zmodyfikuje. Gdy takich produktów nie ma, asystent MUST to powiedzieć zamiast wymyślać produkty.

#### Scenario: Pytanie o zwykłe produkty
- **WHEN** gospodarstwo co tydzień kupuje mleko, ostatnio tydzień temu, mleka nie ma na liście, a członek pyta „czego nam zwykle brakuje?”
- **THEN** asystent proponuje mleko i pyta o potwierdzenie, a lista pozostaje bez zmian

#### Scenario: Potwierdzenie zwykłych produktów
- **WHEN** członek potwierdza propozycję zwykłych produktów
- **THEN** asystent dodaje je jako zapotrzebowania członka z typową ilością

#### Scenario: Brak historii
- **WHEN** gospodarstwo nie ma jeszcze historii zakupów, a członek pyta „co zwykle kupujemy?”
- **THEN** asystent mówi, że nie ma jeszcze zwykłych produktów do podpowiedzenia, i nie zmienia listy

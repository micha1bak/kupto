## ADDED Requirements

### Requirement: Przeglądanie historii zakupów
Członek gospodarstwa MUST móc przeglądać historię zakupów swojego gospodarstwa: zakończenia zakupów od najnowszych, doczytywane porcjami. Każde zakończenie MUST pokazywać czas, członka, który je wykonał, oraz kupione pozycje pogrupowane po kategorii — z czasem i autorem zakupu, zgłaszającymi i sumą ilości w każdej jednostce. Członek MUST NOT widzieć historii innego gospodarstwa. Historia MUST NOT pokazywać kwot ani wydatków.

#### Scenario: Najnowsze zakończenie pierwsze
- **WHEN** ala zakończyła zakupy w poniedziałek, a ola we wtorek
- **THEN** historia pokazuje najpierw zakończenie oli, potem ali

#### Scenario: Szczegóły pozycji
- **WHEN** ala zgłosiła 2 l mleka, ola 1 l mleka, ola kupiła mleko, a ala zakończyła zakupy
- **THEN** w zakończeniu ali, w grupie Nabiał, jest mleko kupione przez olę, ze zgłaszającymi alą i olą i sumą 3 l

#### Scenario: Doczytywanie starszych zakończeń
- **WHEN** gospodarstwo ma więcej zakończeń, niż mieści się na jednej stronie
- **THEN** członek widzi najnowsze zakończenia i może doczytać kolejne, starsze, bez powtórzeń i pominięć

#### Scenario: Pusta historia
- **WHEN** w gospodarstwie nikt jeszcze nie zakończył zakupów
- **THEN** historia jest pusta, a widok informuje, że nie ma jeszcze zakończonych zakupów

#### Scenario: Historia innego gospodarstwa
- **WHEN** ewa z innego gospodarstwa przegląda historię
- **THEN** nie widzi zakończeń gospodarstwa ali

### Requirement: Wyszukiwanie produktu w historii
Członek gospodarstwa MUST móc wyszukać produkt w historii zakupów swojego gospodarstwa po fragmencie nazwy, bez względu na wielkość liter i polskie znaki. Dla każdego pasującego produktu wynik MUST zawierać, kiedy i kto ostatnio go kupił oraz ile razy był kupowany; ostatnio kupione produkty MUST być pierwsze.

#### Scenario: Kiedy ostatnio kupowaliśmy
- **WHEN** ola kupiła kawę tydzień temu, a ala wczoraj, i ktoś wyszukuje „KAWA”
- **THEN** wynik pokazuje kawę kupioną ostatnio wczoraj przez alę, kupowaną 2 razy

#### Scenario: Bez polskich znaków
- **WHEN** w historii jest „żółty ser”, a członek wyszukuje „zolty”
- **THEN** wynik zawiera „żółty ser”

#### Scenario: Brak wyników
- **WHEN** członek wyszukuje produkt, którego nikt w gospodarstwie nie kupował
- **THEN** wynik jest pusty

#### Scenario: Wyszukiwanie nie wychodzi poza gospodarstwo
- **WHEN** inne gospodarstwo kupowało kawę, a gospodarstwo ali nie
- **THEN** wyszukiwanie „kawa” przez alę nic nie zwraca

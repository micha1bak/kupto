## ADDED Requirements

### Requirement: Baza przepisów gospodarstwa
Członek gospodarstwa MUST móc zapisać przepis z nazwą, porcjami, adresem źródła, opisem przygotowania i uporządkowaną listą składników (nazwa, ilość z jednostką listy, notatka, kategoria). Przepisy MUST być wspólne dla gospodarstwa: każdy członek MUST móc je przeglądać, zmieniać i usuwać; inne gospodarstwa MUST NOT mieć do nich dostępu. Nazwa MUST być unikalna w gospodarstwie bez względu na wielkość liter, a identyfikator przepisu MUST być stały.

#### Scenario: Dodanie przepisu
- **WHEN** ala zapisuje przepis „Naleśniki” ze składnikami mąka (2 szklanki), mleko 0,5 l i jajka 2 szt
- **THEN** ola z tego samego gospodarstwa widzi „Naleśniki” na liście przepisów, a w szczegółach składniki w tej samej kolejności

#### Scenario: Zajęta nazwa
- **WHEN** w gospodarstwie jest już przepis „Naleśniki” i członek zapisuje kolejny przepis „naleśniki”
- **THEN** system odrzuca zapis z kodem 409, a istniejący przepis pozostaje bez zmian

#### Scenario: Edycja przepisu
- **WHEN** ola zmienia przepis „Naleśniki” zapisany przez alę, dodając składnik „cukier”
- **THEN** przepis ma ten sam identyfikator i nowy zestaw składników

#### Scenario: Izolacja gospodarstw
- **WHEN** ewa z innego gospodarstwa odczytuje, zmienia lub usuwa przepis gospodarstwa ali
- **THEN** system odpowiada kodem 404

### Requirement: Składniki przepisu na listę
Członek MUST móc wybrać składniki zapisanego przepisu i dodać je na listę jako swoje zapotrzebowania. Każde takie zapotrzebowanie MUST mieć ilość i jednostkę składnika oraz notatkę „na: <nazwa przepisu>”, uzupełnioną o notatkę składnika w nawiasie, gdy ją ma. Składnik, którego produkt jest już na liście, MUST zostać scalony z istniejącą pozycją i oznaczony w odpowiedzi. Składniki niewybrane MUST NOT trafić na listę.

#### Scenario: Dodanie brakujących składników
- **WHEN** ala w przepisie „Naleśniki” zaznacza mleko (0,5 l) i mąkę (notatka „2 szklanki”) i wybiera „Dodaj zaznaczone na listę”
- **THEN** na liście są zapotrzebowania ali: mleko 0,5 l z notatką „na: Naleśniki” i mąka z notatką „na: Naleśniki (2 szklanki)”, a jajek nie ma

#### Scenario: Produkt już na liście
- **WHEN** na liście jest mleko, a ala dodaje z przepisu mleko
- **THEN** mleko ma drugie zapotrzebowanie na tej samej pozycji, a odpowiedź oznacza je jako już będące na liście

#### Scenario: Składnik z innego przepisu
- **WHEN** żądanie dodania wskazuje składnik, który nie należy do przepisu
- **THEN** system odpowiada kodem 404 i nie zmienia listy

### Requirement: Przepisy w aplikacji
Aplikacja MUST mieć stronę „Przepisy” z listą przepisów gospodarstwa, szczegółami przepisu, formularzem dodania i edycji (z dodawaniem i usuwaniem wierszy składników) oraz usuwaniem przepisu po potwierdzeniu. W szczegółach członek MUST móc zaznaczyć brakujące składniki (domyślnie żaden nie jest zaznaczony) i dodać je na listę, po czym MUST zobaczyć, co dodano.

#### Scenario: Lista z zapisanego przepisu w UI
- **WHEN** ala otwiera przepis, zaznacza dwa składniki i wybiera „Dodaj zaznaczone na listę”
- **THEN** aplikacja dodaje tylko te dwa składniki i pokazuje komunikat z ich nazwami

#### Scenario: Przepis zapisany przez czat
- **WHEN** ala zapisała przepis przez czat i otwiera stronę „Przepisy”
- **THEN** przepis jest widoczny na liście

## MODIFIED Requirements

### Requirement: Jedna aktywna lista na gospodarstwo
Każde gospodarstwo MUST mieć dokładnie jedną aktywną listę zakupów, wspólną i widoczną dla wszystkich jego członków. Użytkownik MUST NOT mieć dostępu do listy innego gospodarstwa (404). Zawartość listy MUST być identyczna dla wszystkich członków; kolejność grup kategorii i znacznik przypięcia MAY się różnić, bo wynikają z kolejności kategorii danego użytkownika.

#### Scenario: Członkowie widzą tę samą listę
- **WHEN** dwóch członków tego samego gospodarstwa bez przypiętych kategorii pobiera listę
- **THEN** obaj otrzymują identyczną zawartość w tej samej kolejności

#### Scenario: Członkowie z różnymi przypięciami
- **WHEN** jeden członek przypiął kategorię Chemia i higiena na pierwszym miejscu, a drugi nie ma przypięć, i obaj pobierają listę
- **THEN** obaj otrzymują te same pozycje w tych samych grupach, różniące się tylko kolejnością grup i znacznikiem przypięcia

#### Scenario: Próba dostępu do cudzej pozycji
- **WHEN** użytkownik próbuje zmienić pozycję należącą do listy innego gospodarstwa
- **THEN** system zwraca 404 i nie zmienia pozycji

## ADDED Requirements

### Requirement: Automatyczna kolejność kategorii
Lista MUST być zwracana z grupami kategorii w kolejności kategorii zalogowanego użytkownika, pomijając kategorie bez pozycji. Bez przypięć kolejność ta MUST być kolejnością automatyczną, czyli obecnie kolejnością zbioru kategorii: Warzywa i owoce, Pieczywo, Nabiał, Mięso i ryby, Mrożonki, Produkty suche, Napoje, Słodycze i przekąski, Chemia i higiena, Inne.

#### Scenario: Lista bez przypięć
- **WHEN** użytkownik bez przypiętych kategorii ma na liście „płyn do naczyń”, „mleko” i „chleb”
- **THEN** grupy są w kolejności Pieczywo, Nabiał, Chemia i higiena, a żadna nie jest oznaczona jako przypięta

#### Scenario: Odczyt pełnej kolejności
- **WHEN** użytkownik pobiera swoją kolejność kategorii
- **THEN** otrzymuje wszystkie kategorie ze zbioru, także te bez pozycji na liście, wraz z informacją, które są przypięte

### Requirement: Przypinanie kategorii na wybranym miejscu
Użytkownik MUST móc przenieść kategorię na początek swojej kolejności, na jej koniec albo bezpośrednio za wskazaną kategorię (między dwie sąsiednie grupy na swojej liście); przeniesiona kategoria MUST zostać przypięta na nowym miejscu. Przypięcia MUST być trwałe i osobne dla każdego użytkownika. Wskazanie samej przenoszonej kategorii jako sąsiada MUST zwrócić błąd 400 bez zmian.

#### Scenario: Przeniesienie kategorii na początek
- **WHEN** użytkownik z pozycjami w kategoriach Pieczywo, Nabiał i Chemia i higiena przenosi Chemię i higienę na początek
- **THEN** jego lista ma grupy w kolejności Chemia i higiena, Pieczywo, Nabiał, a Chemia i higiena jest oznaczona jako przypięta

#### Scenario: Przeniesienie między dwie grupy
- **WHEN** użytkownik z pozycjami w kategoriach Pieczywo, Nabiał i Chemia i higiena przenosi Chemię i higienę między Pieczywo a Nabiał
- **THEN** jego lista ma grupy w kolejności Pieczywo, Chemia i higiena, Nabiał

#### Scenario: Przeniesienie na koniec
- **WHEN** użytkownik przenosi Warzywa i owoce na koniec, a potem na liście pojawia się pozycja z kategorii Inne
- **THEN** Warzywa i owoce pozostają ostatnią grupą na jego liście i są przypięte

#### Scenario: Przypięcie nie zmienia listy innych członków
- **WHEN** członek A przypina Chemię i higienę na początku, a członek B pobiera listę
- **THEN** członek B widzi grupy w kolejności automatycznej

#### Scenario: Przypięcie jest trwałe
- **WHEN** użytkownik przypiął kategorię, wylogował się i zalogował ponownie
- **THEN** jego lista ma tę kategorię na tym samym miejscu

#### Scenario: Przeniesienie względem samej siebie
- **WHEN** użytkownik próbuje przenieść Nabiał bezpośrednio za Nabiał
- **THEN** system zwraca 400, a kolejność się nie zmienia

### Requirement: Pierwszeństwo przypiętych kategorii
Przypięte kategorie MUST zajmować swoje miejsca w kolejności użytkownika; nieprzypięte MUST wypełniać pozostałe miejsca w kolejności automatycznej. Kolejne przeniesienie MUST zachować względny układ wcześniej przypiętych kategorii.

#### Scenario: Nowa kategoria na liście nie przesuwa przypiętej
- **WHEN** użytkownik przypiął Chemię i higienę na początku, a na liście pojawia się pozycja z kategorii Warzywa i owoce
- **THEN** Chemia i higiena pozostaje pierwszą grupą, a Warzywa i owoce są za nią

#### Scenario: Kolejne przypięcie
- **WHEN** użytkownik przypiął Chemię i higienę na początku, a potem przenosi Napoje na początek
- **THEN** jego kolejność zaczyna się od Napoje, Chemia i higiena, a obie kategorie są przypięte

### Requirement: Odpinanie kategorii
Użytkownik MUST móc odpiąć pojedynczą kategorię — wraca ona wtedy na miejsce wynikające z kolejności automatycznej, a pozostałe przypięcia zostają. Użytkownik MUST móc też przywrócić automatyczną kolejność, co usuwa wszystkie jego przypięcia.

#### Scenario: Odpięcie kategorii
- **WHEN** użytkownik z przypiętą na początku Chemią i higieną odpina ją
- **THEN** Chemia i higiena wraca na miejsce z kolejności automatycznej i nie jest oznaczona jako przypięta

#### Scenario: Przywrócenie automatycznej kolejności
- **WHEN** użytkownik z kilkoma przypiętymi kategoriami przywraca automatyczną kolejność
- **THEN** jego lista ma grupy w kolejności automatycznej i żadna nie jest przypięta

### Requirement: Przeciąganie nagłówka kategorii
Na liście w UI użytkownik MUST móc przypiąć kategorię, przeciągając jej nagłówek w nowe miejsce. Na ekranie dotykowym przeciąganie MUST zaczynać się dopiero po przytrzymaniu nagłówka; krótkie stuknięcie lub przesunięcie palcem MUST przewijać listę bez zmiany kolejności. Przypięta kategoria MUST być oznaczona i mieć akcję odpięcia; gdy jakaś kategoria jest przypięta, UI MUST oferować przywrócenie automatycznej kolejności.

#### Scenario: Przeciągnięcie po przytrzymaniu
- **WHEN** użytkownik przytrzymuje nagłówek Nabiał i przeciąga go na pierwsze miejsce, przed Pieczywo
- **THEN** po upuszczeniu Nabiał jest pierwszą grupą, oznaczoną jako przypięta, a kolejność jest zapisana

#### Scenario: Przewijanie bez przytrzymania
- **WHEN** użytkownik przesuwa palcem po nagłówku kategorii bez przytrzymania
- **THEN** lista się przewija, a kolejność kategorii się nie zmienia

#### Scenario: Odpięcie z listy
- **WHEN** użytkownik wybiera „Odepnij” przy przypiętej kategorii
- **THEN** kategoria przestaje być oznaczona jako przypięta i wraca na miejsce z kolejności automatycznej

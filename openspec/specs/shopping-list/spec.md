# shopping-list Specification

## Purpose

Utrzymuje wspólną, aktywną listę zakupów gospodarstwa budowaną z zapotrzebowań zgłaszanych przez członków — scaloną, skategoryzowaną i z informacją, kto czego potrzebuje.

## Requirements

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

### Requirement: Zapotrzebowanie jako źródło pozycji
Każda pozycja listy MUST powstawać z co najmniej jednego zapotrzebowania. Zapotrzebowanie MUST zapamiętywać zgłaszającego członka, czas zgłoszenia, opcjonalną ilość z jednostką i opcjonalną notatkę (np. „bez laktozy”).

#### Scenario: Zgłoszenie z ilością i notatką
- **WHEN** członek zgłasza „2 l mleka bez laktozy”
- **THEN** na liście pojawia się pozycja „mleko” z zapotrzebowaniem tego członka: ilość 2, jednostka „l”, notatka „bez laktozy”

### Requirement: Scalanie zapotrzebowań na ten sam produkt
Zapotrzebowania na ten sam produkt MUST być scalane w jedną pozycję, rozpoznawaną po znormalizowanej nazwie (bez względu na wielkość liter i białe znaki). Ilości w tej samej jednostce MUST być sumowane; ilości w różnych jednostkach MUST być pokazywane osobno w ramach tej samej pozycji.

#### Scenario: Dwóch członków zgłasza mleko
- **WHEN** jeden członek zgłasza „mleko” w ilości 1 l, a drugi „ Mleko ” w ilości 2 l
- **THEN** lista zawiera jedną pozycję „mleko” z łączną ilością 3 l i obydwoma zgłaszającymi

#### Scenario: Różne jednostki
- **WHEN** zgłoszono „2 szt. jabłek” i „1 kg jabłek”
- **THEN** lista zawiera jedną pozycję „jabłka” z ilościami „2 szt.” i „1 kg”

#### Scenario: Zgłoszenie bez ilości
- **WHEN** członek zgłasza „chleb” bez ilości
- **THEN** pozycja „chleb” istnieje na liście bez podanej ilości od tego członka

### Requirement: Kategoryzacja pozycji
Każda pozycja MUST mieć dokładnie jedną kategorię z ustalonego zbioru: Warzywa i owoce, Pieczywo, Nabiał, Mięso i ryby, Mrożonki, Produkty suche, Napoje, Słodycze i przekąski, Chemia i higiena, Inne. Lista MUST być zwracana pogrupowana według kategorii.

#### Scenario: Lista pogrupowana
- **WHEN** na liście są „mleko”, „ser żółty” i „płyn do naczyń”
- **THEN** „mleko” i „ser żółty” są w grupie Nabiał, a „płyn do naczyń” w grupie Chemia i higiena

### Requirement: Ręczne dodanie pozycji
Członek MUST móc dodać zapotrzebowanie bez czatu, podając nazwę (1–100 znaków), opcjonalną ilość z jednostką, notatkę i kategorię. Brak kategorii MUST skutkować kategorią Inne, chyba że produkt o tej nazwie był już wcześniej skategoryzowany w tym gospodarstwie. Ręcznie dodane zapotrzebowanie MUST podlegać scalaniu.

#### Scenario: Dodanie znanego produktu bez kategorii
- **WHEN** członek ręcznie dodaje „mleko”, które wcześniej było na liście w kategorii Nabiał
- **THEN** pozycja otrzymuje kategorię Nabiał

#### Scenario: Dodanie nowego produktu bez kategorii
- **WHEN** członek ręcznie dodaje produkt, który nigdy nie był skategoryzowany
- **THEN** pozycja otrzymuje kategorię Inne

### Requirement: Oznaczanie pozycji jako kupionej
Każdy członek MUST móc oznaczyć pozycję jako kupioną i cofnąć to oznaczenie. System MUST zapamiętać, kto i kiedy oznaczył pozycję jako kupioną.

#### Scenario: Odhaczenie pozycji
- **WHEN** członek oznacza „mleko” jako kupione
- **THEN** pozycja pozostaje na liście z oznaczeniem kupionej, nazwą oznaczającego i czasem

#### Scenario: Cofnięcie odhaczenia
- **WHEN** członek cofa oznaczenie kupionej pozycji
- **THEN** pozycja wraca do stanu do kupienia

### Requirement: Usuwanie pozycji i zapotrzebowań
Członek MUST móc usunąć całą pozycję albo wycofać własne zapotrzebowanie. Wycofanie ostatniego zapotrzebowania pozycji MUST usunąć pozycję z listy.

#### Scenario: Wycofanie własnego zapotrzebowania
- **WHEN** członek wycofuje swoje zapotrzebowanie na „mleko”, a inny członek też je zgłosił
- **THEN** pozycja zostaje z zapotrzebowaniem drugiego członka i przeliczoną ilością

#### Scenario: Usunięcie całej pozycji
- **WHEN** członek usuwa pozycję „chleb”
- **THEN** pozycja znika z listy wraz ze wszystkimi zapotrzebowaniami

### Requirement: Zakończenie zakupów
Członek MUST móc zakończyć zakupy: wszystkie pozycje oznaczone jako kupione MUST zostać usunięte z aktywnej listy, a pozostałe MUST zostać bez zmian.

#### Scenario: Zakończenie zakupów z częścią kupionych pozycji
- **WHEN** na liście są kupione „mleko” i niekupiony „chleb”, a członek kończy zakupy
- **THEN** na liście zostaje tylko „chleb”

### Requirement: Widoczność zmian innych członków
Zmiany listy wprowadzone przez jednego członka (przez czat lub ręcznie) MUST być widoczne dla pozostałych członków z otwartą aplikacją najpóźniej po 10 sekundach, bez ręcznego odświeżania strony.

#### Scenario: Zmiana przez innego członka
- **WHEN** członek A dodaje pozycję, a członek B ma otwarty widok listy
- **THEN** pozycja pojawia się u członka B w ciągu 10 sekund

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

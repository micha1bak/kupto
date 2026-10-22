# shopping-list Specification

## Purpose

Utrzymuje wspólną, aktywną listę zakupów gospodarstwa budowaną z zapotrzebowań zgłaszanych przez członków — scaloną, skategoryzowaną i z informacją, kto czego potrzebuje.

## Requirements

### Requirement: Jedna aktywna lista na gospodarstwo
Każde gospodarstwo MUST mieć dokładnie jedną aktywną listę zakupów, wspólną i widoczną dla wszystkich jego członków. Użytkownik MUST NOT mieć dostępu do listy innego gospodarstwa (404).

#### Scenario: Członkowie widzą tę samą listę
- **WHEN** dwóch członków tego samego gospodarstwa pobiera listę
- **THEN** obaj otrzymują identyczną zawartość

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

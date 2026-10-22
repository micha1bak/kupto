## MODIFIED Requirements

### Requirement: Jedna aktywna lista na gospodarstwo
Każde gospodarstwo MUST mieć dokładnie jedną aktywną listę zakupów, wspólną i widoczną dla wszystkich jego członków. Użytkownik MUST NOT mieć dostępu do listy innego gospodarstwa (404). Zawartość listy MUST być identyczna dla wszystkich członków; kolejność grup kategorii, kolejność pozycji w grupie i znaczniki przypięcia MAY się różnić, bo wynikają z kolejności kategorii i produktów danego użytkownika.

#### Scenario: Członkowie widzą tę samą listę
- **WHEN** dwóch członków tego samego gospodarstwa bez przypiętych kategorii i produktów pobiera listę
- **THEN** obaj otrzymują identyczną zawartość w tej samej kolejności

#### Scenario: Członkowie z różnymi przypięciami
- **WHEN** jeden członek przypiął kategorię Chemia i higiena na pierwszym miejscu, a drugi nie ma przypięć, i obaj pobierają listę
- **THEN** obaj otrzymują te same pozycje w tych samych grupach, różniące się tylko kolejnością grup i znacznikiem przypięcia

#### Scenario: Członkowie z różnie przypiętymi produktami
- **WHEN** jeden członek przypiął „mleko” przed „jogurtem” w kategorii Nabiał, a drugi nie ma przypięć, i obaj pobierają listę
- **THEN** obaj otrzymują te same pozycje w tych samych grupach, różniące się tylko kolejnością pozycji w grupie Nabiał i znacznikiem przypięcia pozycji

#### Scenario: Próba dostępu do cudzej pozycji
- **WHEN** użytkownik próbuje zmienić pozycję należącą do listy innego gospodarstwa
- **THEN** system zwraca 404 i nie zmienia pozycji

## ADDED Requirements

### Requirement: Kolejność produktów w kategorii
Pozycje w każdej grupie kategorii MUST być zwracane w kolejności produktów zalogowanego użytkownika, a każda pozycja MUST mieć znacznik, czy jest przypięta. Bez przypięć ta kolejność MUST być kolejnością bazową, czyli obecnie alfabetyczną według znormalizowanej nazwy produktu.

#### Scenario: Grupa bez przypięć
- **WHEN** użytkownik bez przypiętych produktów ma w kategorii Nabiał „ser”, „mleko” i „jogurt”
- **THEN** grupa Nabiał zawiera je w kolejności jogurt, mleko, ser, a żadna pozycja nie jest oznaczona jako przypięta

### Requirement: Przypinanie produktu na wybranym miejscu w kategorii
Użytkownik MUST móc przenieść pozycję na początek swojej kolejności produktów w jej kategorii, na koniec albo między dwie sąsiednie pozycje tej samej kategorii; przeniesiony produkt MUST zostać przypięty. Przypięcie MUST być trwałe, osobne dla każdego użytkownika i dotyczyć produktu (znormalizowanej nazwy), a nie pojedynczej pozycji. Sąsiad z innej kategorii albo sama przenoszona pozycja jako sąsiad MUST dać błąd 400 bez zmian.

#### Scenario: Przeniesienie produktu na początek kategorii
- **WHEN** użytkownik z pozycjami „jogurt”, „mleko”, „ser” w kategorii Nabiał przenosi „ser” na początek
- **THEN** grupa Nabiał ma kolejność ser, jogurt, mleko, a „ser” jest oznaczony jako przypięty

#### Scenario: Przeniesienie produktu między dwie pozycje
- **WHEN** użytkownik z pozycjami „jogurt”, „mleko”, „ser” przenosi „ser” między „jogurt” a „mleko”
- **THEN** grupa Nabiał ma kolejność jogurt, ser, mleko

#### Scenario: Przeniesienie produktu na koniec
- **WHEN** użytkownik przenosi „jogurt” na koniec kategorii Nabiał, a potem na liście pojawia się „twaróg”
- **THEN** „jogurt” pozostaje ostatnią pozycją grupy Nabiał

#### Scenario: Przypięcie działa przy kolejnym dodaniu produktu
- **WHEN** użytkownik przypiął „ser” na początku kategorii Nabiał, zakupy zakończono, a w następnym tygodniu na liście znów są „jogurt”, „mleko” i „ser”
- **THEN** „ser” jest pierwszą pozycją grupy Nabiał i jest oznaczony jako przypięty

#### Scenario: Przypięcie produktu nie zmienia listy innych członków
- **WHEN** członek A przypina „ser” na początku kategorii Nabiał, a członek B pobiera listę
- **THEN** członek B widzi pozycje grupy Nabiał alfabetycznie, bez znacznika przypięcia

#### Scenario: Sąsiad z innej kategorii
- **WHEN** użytkownik próbuje przenieść „ser” (Nabiał) bezpośrednio za „chleb” (Pieczywo)
- **THEN** system zwraca 400, a kolejność się nie zmienia

#### Scenario: Przeniesienie względem samego siebie
- **WHEN** użytkownik próbuje przenieść „ser” bezpośrednio za „ser”
- **THEN** system zwraca 400, a kolejność się nie zmienia

### Requirement: Pierwszeństwo przypiętych produktów
Przypięte produkty MUST zachowywać względny układ ustalony przez użytkownika, także gdy część z nich chwilowo nie jest na liście; nieprzypięte MUST wypełniać pozostałe miejsca w kolejności bazowej. Kolejne przeniesienie MUST zachować względny układ wcześniej przypiętych produktów kategorii.

#### Scenario: Nowy produkt nie przesuwa przypiętego
- **WHEN** użytkownik przypiął „ser” na początku kategorii Nabiał, a na liście pojawia się „bita śmietana”
- **THEN** „ser” pozostaje pierwszą pozycją grupy Nabiał, a „bita śmietana” jest za nim

#### Scenario: Produkt przypięty między innymi zostaje za swoim poprzednikiem
- **WHEN** użytkownik przypiął „ser” między „jogurtem” a „mlekiem”, a na liście pojawia się „bita śmietana”
- **THEN** grupa Nabiał ma kolejność bita śmietana, jogurt, ser, mleko

#### Scenario: Kolejne przypięcie produktu
- **WHEN** użytkownik przypiął „ser” na początku kategorii Nabiał, a potem przenosi „mleko” na początek
- **THEN** grupa Nabiał zaczyna się od mleko, ser, a oba produkty są przypięte

#### Scenario: Nieobecny przypięty produkt zachowuje swoje miejsce
- **WHEN** użytkownik ułożył przypięte „ser”, „mleko”, „jogurt” w tej kolejności, a na liście są tylko „jogurt” i „ser”
- **THEN** grupa Nabiał ma kolejność ser, jogurt

### Requirement: Odpinanie produktu
Użytkownik MUST móc odpiąć produkt — wraca on wtedy na miejsce wynikające z kolejności bazowej w swojej kategorii, a pozostałe przypięcia zostają.

#### Scenario: Odpięcie produktu
- **WHEN** użytkownik z przypiętym na początku kategorii Nabiał „serem” odpina go
- **THEN** „ser” wraca na miejsce z kolejności alfabetycznej i nie jest oznaczony jako przypięty

### Requirement: Przeciąganie produktu
Na liście w UI użytkownik MUST móc przypiąć produkt, przeciągając jego wiersz za uchwyt w nowe miejsce w tej samej kategorii. Na ekranie dotykowym przeciąganie MUST zaczynać się dopiero po przytrzymaniu uchwytu; stuknięcie w pole wyboru MUST odhaczać pozycję, a przesunięcie palcem MUST przewijać listę bez zmiany kolejności. Przypięty produkt MUST być oznaczony i mieć akcję odpięcia. Przeciąganie nagłówków kategorii MUST działać jak dotąd.

#### Scenario: Przeciągnięcie produktu po przytrzymaniu
- **WHEN** użytkownik przytrzymuje uchwyt pozycji „ser” i przeciąga ją na pierwsze miejsce grupy Nabiał
- **THEN** po upuszczeniu „ser” jest pierwszą pozycją grupy, oznaczoną jako przypięta, a kolejność jest zapisana

#### Scenario: Odhaczanie i przewijanie bez przytrzymania
- **WHEN** użytkownik stuka w pole wyboru pozycji albo przesuwa palcem po liście bez przytrzymania uchwytu
- **THEN** pozycja zostaje odhaczona albo lista się przewija, a kolejność produktów się nie zmienia

#### Scenario: Odpięcie produktu z listy
- **WHEN** użytkownik wybiera „Odepnij” przy przypiętym produkcie
- **THEN** produkt przestaje być oznaczony jako przypięty i wraca na miejsce z kolejności alfabetycznej

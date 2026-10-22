## MODIFIED Requirements

### Requirement: Automatyczna kolejność kategorii
Lista MUST być zwracana z grupami kategorii w kolejności kategorii zalogowanego użytkownika, pomijając kategorie bez pozycji. Bez przypięć kolejność ta MUST być kolejnością automatyczną, czyli kolejnością wyuczoną z historii odhaczeń (wymaganie „Wyuczona kolejność kategorii i produktów”), a bez takiej historii — kolejnością zbioru kategorii: Warzywa i owoce, Pieczywo, Nabiał, Mięso i ryby, Mrożonki, Produkty suche, Napoje, Słodycze i przekąski, Chemia i higiena, Inne.

#### Scenario: Lista bez przypięć
- **WHEN** użytkownik bez przypiętych kategorii, w gospodarstwie bez historii zakupów, ma na liście „płyn do naczyń”, „mleko” i „chleb”
- **THEN** grupy są w kolejności Pieczywo, Nabiał, Chemia i higiena, a żadna nie jest oznaczona jako przypięta

#### Scenario: Odczyt pełnej kolejności
- **WHEN** użytkownik pobiera swoją kolejność kategorii
- **THEN** otrzymuje wszystkie kategorie ze zbioru, także te bez pozycji na liście, w swojej kolejności (automatycznej z uwzględnieniem przypięć), wraz z informacją, które są przypięte

## ADDED Requirements

### Requirement: Wyuczona kolejność kategorii i produktów
Kolejność bazowa kategorii i produktów (ta, wokół której układają się przypięcia) MUST być wyuczona z kolejności odhaczeń użytkownika w zakończonych zakupach gospodarstwa: z ostatnich 10 przejść (odhaczeń jednej osoby w jednym zakończeniu zakupów, co najmniej 2 pozycje). Element obecny w co najmniej 2 przejściach MUST stać według mediany swojego względnego miejsca; pozostałe MUST zostać na miejscach z dotychczasowej kolejności bazowej.

#### Scenario: Kolejność z własnych odhaczeń
- **WHEN** ala w trzech zakończeniach zakupów odhaczała kolejno „płyn do naczyń”, „mleko”, „chleb”, a teraz ma je znowu na liście i nic nie przypięła
- **THEN** jej grupy są w kolejności Chemia i higiena, Nabiał, Pieczywo

#### Scenario: Kolejność produktów z odhaczeń
- **WHEN** ala w trzech zakończeniach zakupów odhaczała w Nabiale kolejno „ser”, „mleko”, „jogurt”, a teraz ma je znowu na liście
- **THEN** jej grupa Nabiał ma kolejność ser, mleko, jogurt

#### Scenario: Członkowie z różnymi nawykami
- **WHEN** ala zwykle odhacza „chleb” przed „mlekiem”, a ewa z tego samego gospodarstwa „mleko” przed „chlebem”, i obie mają co najmniej 3 własne przejścia
- **THEN** obie widzą te same pozycje, ala z Pieczywem przed Nabiałem, a ewa z Nabiałem przed Pieczywem

#### Scenario: Element bez historii zostaje na swoim miejscu
- **WHEN** ala ma wyuczoną kolejność „ser” przed „mlekiem”, a na liście pojawia się „jogurt”, którego nigdy nie odhaczała
- **THEN** grupa Nabiał ma kolejność jogurt, ser, mleko — „jogurt” na swoim alfabetycznym miejscu, a wyuczone produkty zamienione miejscami

#### Scenario: Jedno nietypowe przejście nie zmienia kolejności
- **WHEN** ala w czterech zakończeniach zakupów odhaczała „chleb” przed „mlekiem”, a w piątym odwrotnie
- **THEN** jej Pieczywo nadal jest przed Nabiałem

### Requirement: Zimny start kolejności wyuczonej
Gdy użytkownik ma mniej niż 3 własne przejścia, kolejność MUST być wyuczona z przejść wszystkich członków gospodarstwa, jeśli jest ich co najmniej 3; w przeciwnym razie MUST być dotychczasową kolejnością bazową (stała kolejność kategorii, alfabetyczna produktów). Historia innych gospodarstw MUST NOT wpływać na kolejność.

#### Scenario: Zimny start z historii gospodarstwa
- **WHEN** nowy członek gospodarstwa nie ma własnych przejść, a domownicy w trzech zakończeniach zakupów odhaczali „płyn do naczyń” przed „chlebem”
- **THEN** nowy członek widzi Chemię i higienę przed Pieczywem

#### Scenario: Zimny start bez historii
- **WHEN** gospodarstwo ma mniej niż 3 przejścia z co najmniej 2 pozycjami
- **THEN** kategorie są w stałej kolejności zbioru, a produkty alfabetycznie

#### Scenario: Historia innego gospodarstwa
- **WHEN** inne gospodarstwo w wielu zakończeniach zakupów odhaczało „płyn do naczyń” przed „chlebem”, a gospodarstwo ali nie ma historii
- **THEN** ala widzi kategorie w stałej kolejności zbioru

### Requirement: Stabilność kolejności wyuczonej
Kolejność wyuczona MUST zmieniać się tylko po zakończeniu zakupów, a nie przy odhaczaniu lub cofaniu odhaczenia pozycji.

#### Scenario: Odhaczanie nie przestawia listy
- **WHEN** ala w trakcie zakupów odhacza pozycje w innej kolejności niż zwykle
- **THEN** kolejność jej listy nie zmienia się do zakończenia zakupów

### Requirement: Pierwszeństwo przypięć przed kolejnością wyuczoną
Przypięte kategorie i produkty MUST mieć pierwszeństwo przed kolejnością wyuczoną: zajmują swoje miejsca jak dotąd, a nieprzypięte MUST układać się wokół nich w kolejności wyuczonej.

#### Scenario: Przypięcie ma pierwszeństwo
- **WHEN** ala ma wyuczoną kolejność Chemia i higiena przed Pieczywem, a przypięła Pieczywo na pierwszym miejscu
- **THEN** Pieczywo jest pierwsze, a nieprzypięte kategorie układają się za nim w kolejności wyuczonej

#### Scenario: Przypięty produkt na tle kolejności wyuczonej
- **WHEN** ala ma wyuczoną kolejność „ser”, „mleko”, „jogurt”, a przypięła „jogurt” na początku Nabiału
- **THEN** grupa Nabiał ma kolejność jogurt, ser, mleko

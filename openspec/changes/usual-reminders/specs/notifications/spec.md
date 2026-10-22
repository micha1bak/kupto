## ADDED Requirements

### Requirement: Przypomnienie o zwykłych produktach
Raz dziennie system MUST wysłać członkom gospodarstwa, którzy włączyli przypomnienia, powiadomienie z nazwami zwykle kupowanych produktów, których brakuje na liście (te same produkty co w podpowiedziach przy liście). Kliknięcie MUST otwierać listę. Gdy gospodarstwu nie brakuje żadnego zwykłego produktu, przypomnienie MUST NOT być wysyłane. Przypomnienie MUST zawierać wyłącznie produkty z historii gospodarstwa adresata.

#### Scenario: Brakuje zwykłego produktu
- **WHEN** gospodarstwo ali kupuje mleko co tydzień, ostatnio tydzień temu, mleka nie ma na liście, a ala włączyła przypomnienia
- **THEN** o porze przypomnień ala dostaje „Zwykle o tej porze kupujecie” z treścią „mleko — dopisać do listy?”

#### Scenario: Nic nie brakuje
- **WHEN** wszystkie zwykłe produkty gospodarstwa są na liście albo zostały niedawno kupione
- **THEN** nikt z gospodarstwa nie dostaje przypomnienia

#### Scenario: Inne gospodarstwo
- **WHEN** gospodarstwu ewy brakuje zwykłej kawy, a gospodarstwu ali niczego
- **THEN** ewa dostaje przypomnienie o kawie, a ala nie dostaje nic

### Requirement: Częstotliwość przypomnień
Gospodarstwo MUST dostać najwyżej jedno przypomnienie o zwykłych produktach na dobę czasu polskiego, a przypomnienie MUST być wysyłane tylko między 9:00 a 21:00 czasu polskiego. Przypomnienie MUST być wysyłane tylko wtedy, gdy co najmniej jeden brakujący produkt nie był jeszcze przypominany od czasu jego ostatniego zakupu; te same produkty bez zmiany MUST NOT wracać w kolejnych przypomnieniach.

#### Scenario: Ponowne uruchomienie tego samego dnia
- **WHEN** gospodarstwo dostało dziś przypomnienie, a wysyłka przypomnień uruchamia się ponownie
- **THEN** gospodarstwo nie dostaje drugiego przypomnienia

#### Scenario: Te same produkty następnego dnia
- **WHEN** wczoraj przypomniano o mleku, mleka nadal nie ma na liście ani nie zostało kupione
- **THEN** dziś gospodarstwo nie dostaje przypomnienia

#### Scenario: Nowy produkt następnego dnia
- **WHEN** wczoraj przypomniano o mleku, a dziś brakuje też chleba
- **THEN** gospodarstwo dostaje przypomnienie z chlebem i mlekiem

#### Scenario: Kolejny zakup
- **WHEN** przypomniano o mleku, potem gospodarstwo kupiło mleko, a po typowym odstępie znów go brakuje
- **THEN** gospodarstwo znów dostaje przypomnienie o mleku

#### Scenario: Noc
- **WHEN** wysyłka przypomnień uruchamia się o 3:00 czasu polskiego (np. nadrobiona po starcie serwera)
- **THEN** nikt nie dostaje przypomnienia, a przypomnienie może przyjść tego samego dnia o zwykłej porze

### Requirement: Przypomnienia domyślnie wyłączone
Typ powiadomień „Zwykłe produkty” MUST być domyślnie wyłączony i MUST dać się włączyć i wyłączyć jak pozostałe typy powiadomień. Gdy żaden członek gospodarstwa nie chce przypomnień lub nie ma urządzenia z włączonymi powiadomieniami, gospodarstwo MUST być pomijane tak, jakby przypomnienia nie było, żeby po włączeniu przypomnień przyszły także produkty brakujące już wcześniej.

#### Scenario: Domyślnie wyłączone
- **WHEN** ala, która nie zmieniała ustawień, otwiera ustawienia powiadomień
- **THEN** typ „Zwykłe produkty” jest wyłączony, a pozostałe typy włączone

#### Scenario: Włączone tylko przez jednego domownika
- **WHEN** ala włączyła przypomnienia, a ola nie
- **THEN** przypomnienie dostaje tylko ala

#### Scenario: Włączenie po czasie
- **WHEN** gospodarstwu od kilku dni brakuje mleka, nikt nie miał włączonych przypomnień, a dziś ala je włącza
- **THEN** przy najbliższej wysyłce ala dostaje przypomnienie o mleku

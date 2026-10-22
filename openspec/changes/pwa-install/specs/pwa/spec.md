## ADDED Requirements

### Requirement: Instalowalna aplikacja
Aplikacja MUST udostępniać manifest aplikacji webowej z nazwą „Kupto”, trybem wyświetlania `standalone`, adresem startowym w obrębie aplikacji, kolorem tła i kolorem motywu zgodnymi z jasnym motywem interfejsu oraz ikonami 192×192 i 512×512 px, w tym co najmniej jedną ikoną maskowalną. Strona MUST wskazywać ikonę `apple-touch-icon` 180×180 px bez przezroczystości. Strona MUST deklarować kolor paska systemowego zgodny z nagłówkiem aplikacji w motywie jasnym i ciemnym.

#### Scenario: Manifest jest dostępny
- **WHEN** przeglądarka pobiera manifest wskazany przez stronę główną
- **THEN** otrzymuje manifest z nazwą „Kupto”, `display: standalone`, `start_url` w obrębie aplikacji, ikonami 192 i 512 px oraz ikoną o przeznaczeniu `maskable`

#### Scenario: Ikona na iPhonie
- **WHEN** użytkownik iPhone'a dodaje aplikację do ekranu początkowego
- **THEN** jako ikona używany jest nieprzezroczysty obraz 180×180 px wskazany przez `apple-touch-icon`

#### Scenario: Uruchomienie z ekranu głównego
- **WHEN** użytkownik uruchamia zainstalowaną aplikację z ikony
- **THEN** aplikacja otwiera się bez paska adresu przeglądarki, na stronie startowej aplikacji

### Requirement: Pamięć podręczna powłoki aplikacji
W przeglądarkach obsługujących service workery aplikacja MUST rejestrować service worker, który po instalacji przechowuje w pamięci podręcznej powłokę aplikacji bieżącej wersji: dokument HTML, skrypty i style z buildu, ikony i manifest. Skrypty, style i ikony powłoki MUST być serwowane z pamięci podręcznej bez czekania na sieć. Brak obsługi service workerów MUST NOT blokować działania aplikacji.

#### Scenario: Pliki powłoki z pamięci podręcznej
- **WHEN** użytkownik, który już raz otworzył aplikację, otwiera ją ponownie
- **THEN** skrypty, style i ikony bieżącej wersji są wczytywane z pamięci podręcznej, bez pobierania ich przez sieć

#### Scenario: Przeglądarka bez service workerów
- **WHEN** przeglądarka nie obsługuje service workerów
- **THEN** aplikacja działa jak dotąd, pobierając wszystko z sieci

### Requirement: Dokument HTML najpierw z sieci
Dokument HTML aplikacji MUST być pobierany najpierw z sieci. Gdy sieć nie odpowie w ciągu kilku sekund lub jest niedostępna, MUST zostać użyta wersja z pamięci podręcznej.

#### Scenario: Ponowne otwarcie przy słabym zasięgu
- **WHEN** użytkownik, który już raz otworzył aplikację, otwiera ją ponownie, a sieć nie odpowiada przez kilka sekund
- **THEN** powłoka aplikacji ładuje się z pamięci podręcznej, a dane listy są pobierane, gdy tylko sieć odpowie

### Requirement: API zawsze z sieci
Żądania do `/api/*` (w tym lista zakupów, strumień czatu, logowanie i wylogowanie) MUST NOT być obsługiwane z pamięci podręcznej service workera ani w niej zapisywane — zawsze trafiają do sieci bez pośrednictwa pamięci podręcznej. Żądania inne niż `GET` oraz żądania do innych domen MUST być przekazywane do sieci bez zmian.

#### Scenario: Odświeżenie listy
- **WHEN** aplikacja kontrolowana przez service worker odpytuje `/api/list`
- **THEN** odpowiedź pochodzi z serwera, a nie z pamięci podręcznej, i nie jest w niej zapisywana

#### Scenario: Strumień czatu
- **WHEN** użytkownik wysyła wiadomość czatu (`POST /api/chat/messages`)
- **THEN** żądanie trafia do serwera bez pośrednictwa service workera, a odpowiedź jest strumieniowana jak dotąd

#### Scenario: Wylogowanie i ponowne logowanie
- **WHEN** użytkownik wylogowuje się, a następnie loguje jako inna osoba
- **THEN** profil i dane pochodzą z serwera dla nowej sesji, bez danych poprzedniego użytkownika z pamięci podręcznej

### Requirement: Aktualizacja do nowej wersji
Po wdrożeniu nowej wersji frontendu użytkownik MUST otrzymać ją bez ręcznego czyszczenia danych przeglądarki: najpóźniej przy następnym otwarciu aplikacji z dostępem do sieci albo — w aplikacji pozostawionej w tle — po kolejnym powrocie do niej. Po aktywacji nowej wersji pamięć podręczna poprzednich wersji MUST zostać usunięta. Aktualizacja MUST NOT przeładowywać strony, na którą użytkownik w danej chwili patrzy.

#### Scenario: Otwarcie po wdrożeniu
- **WHEN** po wdrożeniu nowej wersji użytkownik otwiera aplikację z dostępem do sieci
- **THEN** widzi nową wersję interfejsu

#### Scenario: Aplikacja pozostawiona w tle
- **WHEN** zainstalowana aplikacja była otwarta w tle podczas wdrożenia, a użytkownik do niej wraca
- **THEN** aplikacja sprawdza dostępność nowej wersji, a po jej aktywacji przełącza się na nią przy najbliższym przejściu w tło, bez przeładowania na oczach użytkownika

### Requirement: Nagłówki plików PWA
Plik service workera i manifest MUST być serwowane z nagłówkiem `Cache-Control: no-cache`, a żądanie nieistniejącego pliku pod tymi adresami MUST zwracać 404 zamiast strony aplikacji.

#### Scenario: Nagłówki pliku service workera
- **WHEN** przeglądarka pobiera `/sw.js` lub `/manifest.webmanifest`
- **THEN** odpowiedź ma nagłówek `Cache-Control: no-cache`, a brak pliku daje 404 zamiast strony aplikacji

### Requirement: Kiedy pokazywać baner instalacji
Na stronie głównej aplikacji (po zalogowaniu) MUST pojawiać się baner zachęcający do instalacji, gdy aplikacja nie działa w trybie zainstalowanym, przeglądarka pozwala ją zainstalować (programowo albo — na iPhonie i iPadzie — z menu Udostępnij), a użytkownik nie zamknął banera na tym urządzeniu w ciągu ostatnich 30 dni. W pozostałych przypadkach baner MUST NOT się pojawiać.

#### Scenario: Zamknięcie banera
- **WHEN** użytkownik zamyka baner, a potem ponownie otwiera aplikację
- **THEN** baner nie pojawia się przez kolejne 30 dni

#### Scenario: Aplikacja zainstalowana
- **WHEN** użytkownik uruchamia aplikację z ekranu głównego (tryb `standalone`)
- **THEN** baner się nie pojawia

#### Scenario: Przeglądarka bez możliwości instalacji
- **WHEN** użytkownik otwiera aplikację w przeglądarce komputera, która nie zgłasza możliwości instalacji
- **THEN** baner się nie pojawia

### Requirement: Treść banera instalacji
W przeglądarkach oferujących programowe okno instalacji baner MUST zawierać przycisk instalacji, który je otwiera. Na iPhonie i iPadzie baner MUST zawierać instrukcję Udostępnij → „Do ekranu początkowego” oraz informację, że powiadomienia wymagają tam instalacji aplikacji. Baner MUST dać się zamknąć.

#### Scenario: Android z Chrome
- **WHEN** użytkownik Androida otwiera aplikację w Chrome, a przeglądarka zgłasza możliwość instalacji
- **THEN** widzi baner z przyciskiem „Zainstaluj”, który otwiera systemowe okno instalacji

#### Scenario: Instalacja zaakceptowana
- **WHEN** użytkownik potwierdza instalację w systemowym oknie
- **THEN** baner znika

#### Scenario: iPhone w Safari
- **WHEN** użytkownik iPhone'a otwiera aplikację w przeglądarce
- **THEN** widzi baner z instrukcją Udostępnij → „Do ekranu początkowego” i informacją, że powiadomienia na iPhonie wymagają dodania aplikacji do ekranu początkowego

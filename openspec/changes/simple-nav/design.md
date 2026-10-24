# Design

## Context

Nagłówek (`layout/MainPage.tsx`) zawiera tytuł „Kupto” i `nav` z linkami Przepisy, Historia, nazwą gospodarstwa (link do `/household`), loginem i przyciskiem „Wyloguj”. Po #76 linki zawijają się do kolejnych wierszy, żeby nie poszerzać strony. Podstrony (`/household`, `/history`, `/recipes`) mają własny link „← Wróć do listy” i własne wcięcie safe-area u góry. Czat asystenta to jeden wątek użytkownika w gospodarstwie (`GET/DELETE /api/chat/messages`); przycisk „Wyczyść historię” jest w nagłówku `ChatView`.

## Goals / Non-Goals

**Goals:**
- Pasek w jednym wierszu przy 320–430 px, bez przewijania w bok, z zachowaniem safe-area z #76.
- Nic z dotychczasowego paska nie znika bez nowego miejsca.
- Tytuł czatu łatwy do podmiany po #78.

**Non-Goals:**
- Czat grupowy, lista rozmów, nowe endpointy.
- Wspólny pasek na podstronach — podstrony zostają z linkiem powrotu.

## Decisions

### D1. Trzy elementy w siatce `auto minmax(0, 1fr) auto`

„Kupto” i ikona profilu mają stałą szerokość, tytuł czatu bierze resztę i skraca się (`text-overflow: ellipsis`, `white-space: nowrap`). Siatka zamiast zawijania gwarantuje jeden wiersz niezależnie od długości nazwy gospodarstwa. „Kupto” jest linkiem do `/` (główny widok także wtedy, gdy trasa-zapas `*` pokazała go pod innym adresem).

### D2. Tytuł czatu z `chatTitle(profile)`

`chat/chatTitle.ts` zwraca nazwę gospodarstwa (zapasowo „Czat”). Po #78 wystarczy zmienić tę funkcję (np. na nazwę czatu grupowego z profilu lub osobnego zapytania) — pasek i arkusz z niej korzystają.

### D3. Opcje czatu jako arkusz (`role="dialog"`)

Przycisk z tytułem ma `aria-haspopup="dialog"` i `aria-expanded`. Arkusz to modalny panel przy dolnej krawędzi na telefonie (z wcięciem `safe-area-inset-bottom`), wyśrodkowany na szerokim ekranie; zamyka go „Zamknij”, Escape i kliknięcie tła; po otwarciu fokus trafia do arkusza, po zamknięciu wraca na tytuł. Własny komponent zamiast `<dialog>` — jsdom w testach nie obsługuje `showModal()`.

Zawartość: nagłówek z tytułem czatu, „Wyczyść historię czatu” (z `window.confirm`, jak „Opuść gospodarstwo”; nieaktywne, gdy historia jest pusta) i link „Gospodarstwo i domownicy” do `/household`. Listy rozmów nie ma w backendzie — to brak do rozstrzygnięcia w #78, nie budujemy go tutaj.

### D4. Czyszczenie historii poza `ChatView`

Mutacja `DELETE /api/chat/messages` przechodzi do arkusza i ustawia `keys.chat` na `[]`. Lokalne dymki `ChatView` (błędy, wymiana w toku) czyści `MainPage`, montując czat od nowa (`key` zwiększany po wyczyszczeniu) — jawnie, bez nasłuchiwania cache. Wymiana w toku podczas czyszczenia to rzadki przypadek; jej zapisany przez serwer wynik pojawi się przy następnym odświeżeniu historii.

### D5. Strona profilu `/profile`

Układ jak pozostałe podstrony (`.page`, link „← Wróć do listy”). Nagłówek z loginem i nazwą gospodarstwa, linki jako wiersze o wysokości ≥ 44 px, na końcu „Wyloguj” (ta sama funkcja wylogowania z `App.tsx`, przekazywana dotąd do `MainPage`). Link „Plan obiadów” do `/meal-plan` — do czasu merge PR #89 adres trafia w trasę-zapas i pokazuje główny widok, dlatego ta zmiana wchodzi po #89.

### D6. Ikona profilu

Inline SVG (sylwetka) z `aria-hidden`, link z `aria-label="Profil"`, obszar 44×44 px. Bez nowych zależności.

## Risks / Trade-offs

- [Długa nazwa gospodarstwa] → skrócona wielokropkiem w pasku, pełna w arkuszu i na profilu.
- [Przyzwyczajenie do linków w nagłówku] → wszystkie są o jedno stuknięcie dalej, na profilu.
- [Konflikt z PR #89 w `viewport.test.ts`] → sąsiednie zmiany; do rozwiązania przy merge.

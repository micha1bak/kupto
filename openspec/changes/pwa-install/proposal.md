# Proposal

## Why

Kupto jest używane głównie na telefonach, w sklepie — a dziś to zwykła strona w przeglądarce: trzeba ją odszukać w kartach lub zakładkach, otwiera się z paskiem adresu i za każdym razem pobiera całą powłokę aplikacji przez (często słabe) sklepowe łącze. Instalowalna aplikacja (PWA) daje ikonę na ekranie głównym, pełny ekran i szybki start z pamięci podręcznej. Jest też warunkiem powiadomień Web Push (#27): na iPhonie powiadomienia działają wyłącznie w aplikacji dodanej do ekranu początkowego, a Web Push wymaga service workera.

## What Changes

- Manifest aplikacji: nazwa „Kupto”, tryb `standalone`, adres startowy, kolory motywu zgodne z interfejsem, ikony 192/512 px, ikona maskowalna (Android) oraz `apple-touch-icon` 180 px (iPhone). Ikony (koszyk na kolorze akcentu) powstają z własnego źródła SVG skryptem w repozytorium.
- Service worker, który przechowuje powłokę aplikacji (HTML, JS, CSS, ikony, manifest) w pamięci podręcznej przypisanej do wersji buildu, tak by aplikacja otwierała się szybko także przy słabym zasięgu, a po wdrożeniu nowego frontendu użytkownik dostawał nową wersję bez ręcznego czyszczenia danych. Żądania `/api/*` (lista, czat SSE, logowanie) nigdy nie są obsługiwane z pamięci podręcznej — zawsze idą do sieci.
- Service worker jest przygotowany do rozszerzenia o obsługę `push` i `notificationclick` w #27 (bez ich implementacji teraz).
- Baner „Dodaj do ekranu głównego” w układzie aplikacji: na Androidzie/Chrome przycisk instalacji, na iPhonie krótka instrukcja (Udostępnij → „Do ekranu początkowego”) z informacją, że powiadomienia na iPhonie wymagają instalacji. Baner da się zamknąć, nie wraca natrętnie i nie pokazuje się w zainstalowanej aplikacji.
- Nagłówki cache w nginx: `sw.js` i manifest zawsze rewalidowane, żeby aktualizacje docierały od razu.

## Capabilities

### New Capabilities

- `pwa`: instalowalność aplikacji (manifest, ikony), service worker z pamięcią podręczną powłoki i zasadami aktualizacji, wyłączenie API z pamięci podręcznej oraz baner zachęcający do instalacji.

### Modified Capabilities

<!-- Brak — zachowanie listy, czatu, kont i gospodarstw się nie zmienia. -->

## Impact

- **Frontend**: nowy katalog `src/pwa/` (service worker, jego rejestracja i aktualizacja, logika banera, wtyczka Vite budująca `sw.js` z listą plików buildu), komponent banera w `src/layout/`, rejestracja w `main.tsx`, metadane w `index.html`, pliki w `public/` (manifest, ikony, źródła SVG), skrypt generujący ikony.
- **nginx** (`frontend/nginx.conf`): osobne reguły dla `/sw.js` i `/manifest.webmanifest` (`no-cache`, bez przekierowania na `index.html`).
- **Zależności**: brak nowych pakietów npm (własny service worker i mała wtyczka Vite zamiast `vite-plugin-pwa`).
- **Backend, wdrożenie, infrastruktura**: bez zmian. Produkcja już działa po HTTPS (Caddy), co jest wymagane dla service workera.
- **Poza zakresem**: Web Push i powiadomienia (#27), praca offline z danymi listy (lista nadal wymaga sieci), synchronizacja w tle.

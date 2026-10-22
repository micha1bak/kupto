# Tasks

## 1. Manifest i ikony

- [ ] 1.1 Dodać źródła ikon `public/icons/icon.svg` i `public/icons/icon-maskable.svg` oraz skrypt `scripts/generate-icons.sh` generujący `icon-192.png`, `icon-512.png`, `icon-maskable-512.png` i `apple-touch-icon.png` (design D6); weryfikacja: skrypt tworzy PNG o właściwych wymiarach (`file`), obejrzane wizualnie, `apple-touch-icon.png` bez przezroczystości
- [ ] 1.2 Dodać `public/manifest.webmanifest` i metadane w `index.html` (manifest, `theme-color` jasny/ciemny, `apple-touch-icon`, favicon SVG, `apple-mobile-web-app-title`); weryfikacja: `npx vite build` kopiuje pliki do `dist/`, manifest to poprawny JSON z polami ze scenariusza „Manifest jest dostępny”

## 2. Service worker (spec: pwa — pamięć podręczna, API z sieci, aktualizacje)

- [ ] 2.1 Dodać czystą funkcję `routeRequest` (`src/pwa/swRouting.ts`, design D2); weryfikacja: testy Vitest — `/api/list`, `POST /api/chat/messages`, `/api/auth/login`, nawigacja na `/api/docs` bez obsługi; nawigacja na `/` i `/household` → sieć z fallbackiem; plik z precache → cache; inna domena i nieznany plik → bez obsługi
- [ ] 2.2 Dodać `src/pwa/sw.ts` (install/activate/fetch, cache per wersja, limit 3 s dla nawigacji, miejsce na `push` w #27) i wtyczkę `src/pwa/swPlugin.ts` emitującą `sw.js` z listą precache i wersją; weryfikacja: test Vitest funkcji budującej listę precache, `npx vite build` daje `dist/sw.js` bez znaczników i importów, z plikami `assets/` bieżącego buildu
- [ ] 2.3 Dodać rejestrację i obsługę aktualizacji `src/pwa/register.ts` (tylko build produkcyjny, `update()` przy powrocie na pierwszy plan, przeładowanie przy przejściu w tło po `controllerchange`) i wywołać ją w `main.tsx`; weryfikacja: testy Vitest z atrapami `navigator.serviceWorker` i `document` (brak SW, rejestracja, `update()`, brak przeładowania przy pierwszej instalacji, przeładowanie dopiero w tle)
- [ ] 2.4 Dodać w `nginx.conf` reguły dla `/sw.js` i `/manifest.webmanifest` (`no-cache`, `try_files $uri =404`); weryfikacja: `docker build frontend` i `curl -I` na uruchomionym kontenerze pokazują `Cache-Control: no-cache` i poprawny typ MIME, a brakujący plik daje 404

## 3. Baner instalacji (spec: pwa — zachęta do instalacji)

- [ ] 3.1 Dodać `src/pwa/install.ts` (wykrywanie iOS, trybu standalone, zamknięcia z ważnością 30 dni, wariant banera, magazyn zdarzenia `beforeinstallprompt` + `appinstalled`) i wywołać `captureInstallPrompt` w `main.tsx`; weryfikacja: testy Vitest — iPhone/iPad/iPadOS jako Mac/Android/desktop, standalone przez `matchMedia` i `navigator.standalone`, zamknięcie świeże/przeterminowane, niedostępny `localStorage`
- [ ] 3.2 Dodać komponent `src/layout/InstallBanner.tsx` (+ style) i umieścić go w `MainPage`; weryfikacja: testy Vitest — przycisk „Zainstaluj” wywołuje `prompt()` i chowa baner po akceptacji, instrukcja dla iPhone'a z informacją o powiadomieniach, „×” zapisuje zamknięcie, brak banera w trybie standalone i bez możliwości instalacji
- [ ] 3.3 Opisać PWA w `frontend/README.md` (struktura `src/pwa/`, strategia cache i aktualizacji, generowanie ikon); weryfikacja: opis zgodny z design D2–D6

## 4. Integracja

- [ ] 4.1 Uruchomić kroki CI lokalnie (`npm ci`, `npx tsc -b`, `npm test`, `npx vite build`, `docker build frontend`); weryfikacja: wszystkie przechodzą
- [ ] 4.2 Sprawdzić zbudowaną aplikację w przeglądarce (kontener nginx lub `vite preview`): manifest i ikony są serwowane, SW się rejestruje i kontroluje stronę, cache zawiera powłokę, żądania `/api/*` nie trafiają do cache; weryfikacja: opis wyników w PR (z wyszczególnieniem, czego nie sprawdzono, np. instalacji na prawdziwym telefonie)

## Workflow follow-up

- Po scaleniu PR zarchiwizować change (`/opsx:archive`), co utworzy `openspec/specs/pwa/spec.md`.
- Po wdrożeniu sprawdzić instalację na Androidzie (Chrome) i iPhonie (Safari).

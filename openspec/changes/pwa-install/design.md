# Design

## Context

Motywacja: `proposal.md`. Wymagania: `specs/pwa/spec.md`.

Stan obecny, który wpływa na podejście:

- Frontend to SPA (React 19 + Vite 8, build Rolldown). Build daje `index.html` i pliki z hashem treści w `assets/` (bez dzielenia kodu na leniwe kawałki). nginx serwuje `assets/` z `immutable` na rok, resztę z `no-cache` i fallbackiem na `index.html`; `/api/` jest przekazywane do backendu bez buforowania (SSE czatu). Przed nginx stoi Caddy (HTTPS, kompresja) — bez własnego cache.
- Wszystkie dane (profil, lista co 5 s, historia czatu) pochodzą z `/api/*`; sesja to ciasteczko. Bez sieci aplikacja i tak nie pokaże listy — „szybki start” oznacza szybkie wczytanie powłoki, nie pracę offline.
- Użytkownicy: telefony z Androidem (Chrome) i iPhone'y (Safari). iOS nie zgłasza `beforeinstallprompt`, a Web Push (#27) działa tam tylko w aplikacji dodanej do ekranu początkowego (iOS 16.4+).
- `ListView.tsx` jest równolegle zmieniany przez inne prace — baner trafia do `layout/MainPage.tsx`.

## Goals / Non-Goals

**Goals:**

- Spójna wersja powłoki w pamięci podręcznej (HTML i pliki, do których się odwołuje, z jednego buildu), wymieniana w całości przy wdrożeniu.
- Nowa wersja docierająca sama — bez okna „odśwież”, bez przeładowania na oczach użytkownika.
- Service worker, do którego #27 dopisze tylko obsługę `push` / `notificationclick` (i ewentualnie subskrypcję), bez zmiany mechanizmu cache.
- Logika decyzji (trasowanie żądań w SW, wykrywanie iOS/standalone/zamknięcia banera, aktualizacje) w czystych funkcjach testowanych w Vitest.

**Non-Goals:**

- Praca offline z danymi listy, kolejka zmian offline, Background Sync.
- Okno „Dostępna nowa wersja” — zbędne przy strategii z D3.
- Zrzuty ekranu i rozszerzone pola manifestu (`screenshots`, `shortcuts`) dla bogatszego okna instalacji.

## Decisions

### D1. Własny service worker + mała wtyczka Vite zamiast `vite-plugin-pwa`

`vite-plugin-pwa` (Workbox) generuje SW i manifest, ale: wciąga `workbox-build` z dużym drzewem zależności (Babel, Rollup, terser) tylko na potrzeby builda, jego obsługa Vite 8/Rolldown jest świeża, a do własnych zdarzeń (`push` w #27) i tak trzeba przejść na tryb `injectManifest`, czyli pisać SW samemu. Potrzebujemy tylko trzech strategii (D2), co mieści się w ~150 wierszach.

Rozwiązanie: `src/pwa/sw.ts` (TypeScript, bez importów współdzielonych z aplikacją) budowany przez wtyczkę `src/pwa/swPlugin.ts` w `vite.config.ts`. Wtyczka (tylko `vite build`) emituje SW jako osobny kawałek o stałej nazwie `sw.js`, a w `generateBundle` podmienia w nim znaczniki na listę plików do precache (wszystkie pliki z `assets/` z bieżącego buildu + `/`, manifest i ikony z `public/`) oraz identyfikator wersji (skrót tej listy). Dzięki temu `sw.js` zmienia się bajtowo przy każdej zmianie frontendu, co uruchamia standardową aktualizację SW w przeglądarce. W trybie `vite dev` SW nie jest rejestrowany (rejestracja tylko w `import.meta.env.PROD`), żeby nie przeszkadzał w HMR.

Typy: SW korzysta z lokalnie zadeklarowanych, minimalnych interfejsów zdarzeń (`ExtendableEvent`, `FetchEvent`), bo dołączenie biblioteki `WebWorker` do tego samego projektu TS co `DOM` powoduje konflikty typów; osobny `tsconfig` dla jednego pliku byłby nieproporcjonalny.

*Alternatywy:* (a) `vite-plugin-pwa` — jw.; (b) ręczny `public/sw.js` bez listy plików, cache'ujący „w locie” — brak typów i testów, a pierwsza wizyta nie zapełnia cache (strona ładuje się, zanim SW przejmie kontrolę), więc start z cache działałby dopiero od trzeciego otwarcia; (c) parsowanie `index.html` w SW przy instalacji w poszukiwaniu plików — kruche.

### D2. Strategie w SW

Decyzję podejmuje czysta funkcja `routeRequest` (`src/pwa/swRouting.ts`):

| Żądanie | Strategia |
|---|---|
| metoda inna niż `GET`, inna domena, ścieżka `/api` lub `/api/…` | **brak obsługi** — SW nie wywołuje `respondWith`, przeglądarka idzie prosto do sieci; nic nie trafia do cache |
| nawigacja (`mode: navigate`) | **najpierw sieć** z limitem 3 s, potem `/` z cache wersji; odpowiedź z sieci nie jest zapisywana |
| plik z listy precache | **najpierw cache** wersji, w razie braku sieć |
| cokolwiek innego | brak obsługi |

API jest wyłączone jako pierwsza reguła, więc żadna strategia nie może go objąć (także nawigacja na `/api/docs`). Brak `respondWith` (a nie „network-only” przez `fetch` w SW) zachowuje strumieniowanie SSE i ciasteczka dokładnie jak bez SW.

HTML „najpierw z sieci” zamiast „najpierw z cache”: przy dostępnej sieci użytkownik zawsze dostaje aktualny `index.html` (mały, ~1 KB), a ciężkie JS/CSS i tak idą z cache — start jest szybki, a nowa wersja widoczna od razu po wdrożeniu, bez okna „odśwież”. Limit 3 s chroni przed zawieszonym łączem w sklepie. Odpowiedź nawigacji nie jest zapisywana, by cache zawierał zawsze spójny zestaw z jednego buildu (nowy HTML z sieci przy starym SW pobierze brakujące pliki z sieci — nginx je ma).

### D3. Cykl życia i aktualizacje

- Cache nazywa się `kupto-shell-<wersja>`. `install`: pobranie całej listy precache (`cache: "reload"`, z pominięciem cache HTTP), potem `skipWaiting()`. `activate`: usunięcie wszystkich cache `kupto-shell-*` innych wersji i `clients.claim()`.
- Rejestracja (`src/pwa/register.ts`): `register("/sw.js", { scope: "/", updateViaCache: "none" })` po zdarzeniu `load`. Przeglądarka sprawdza `sw.js` przy każdej nawigacji; dodatkowo przy powrocie strony na pierwszy plan (`visibilitychange` → `visible`) wywołujemy `registration.update()`, bo zainstalowana aplikacja wznowiona z tła nie nawiguje.
- Gdy nowy SW przejmie stronę, która już była kontrolowana (`controllerchange` przy istniejącym wcześniej kontrolerze — nie przy pierwszej instalacji), strona jest przeładowywana **przy najbliższym przejściu w tło** (`visibilitychange` → `hidden`), a jeśli już jest w tle — od razu. Użytkownik po powrocie widzi nową wersję, a przeładowanie nie przerywa mu pracy na ekranie. Bez tego aplikacja trzymana w tle na Androidzie działałaby na starym JS całymi dniami.
- nginx: `location = /sw.js` i `location = /manifest.webmanifest` z `Cache-Control: no-cache` i `try_files $uri =404` (brak pliku nie może zwrócić `index.html`). Ikony zostają pod `location /` (`no-cache`, rewalidacja ETag).
- Wycofanie: wdrożenie poprzedniego obrazu zmienia `sw.js`, więc przeglądarki aktualizują się „wstecz” tak samo. Awaryjnie można opublikować SW, który w `activate` czyści cache i się wyrejestrowuje (bez zmian w nginx).

### D4. Rozszerzalność pod Web Push (#27)

`sw.ts` ma wydzielone sekcje: cykl życia, `fetch` i miejsce na `push` / `notificationclick` (komentarz). Rejestracja zwraca `ServiceWorkerRegistration`, z której #27 skorzysta do `pushManager.subscribe`. Zakres SW to `/`, więc obejmie całą aplikację.

### D5. Baner instalacji

- `src/pwa/install.ts` — czyste funkcje: `isIos(navigator)` (iPhone/iPod/iPad w UA oraz iPadOS udający Maca: `MacIntel` + `maxTouchPoints > 1`), `isStandalone(window)` (`display-mode: standalone`/`fullscreen` lub `navigator.standalone`), `isDismissed(storage, now)` (znacznik czasu w `localStorage` pod `kupto.installBanner.dismissedAt`, ważny 30 dni; błędy dostępu do `localStorage`, np. w trybie prywatnym, traktowane jak „nie zamknięto”, a zapis — jak no-op), `bannerVariant(...)` → `"prompt" | "ios" | null`.
- `beforeinstallprompt` może przyjść, zanim React zamontuje układ (np. podczas logowania), więc nasłuch jest zakładany w `main.tsx` (`captureInstallPrompt`), a zdarzenie (po `preventDefault()`) trzymane w małym magazynie modułowym, czytanym przez `useSyncExternalStore`. `appinstalled` czyści zdarzenie i ukrywa baner.
- Komponent `src/layout/InstallBanner.tsx` w `MainPage` między zakładkami a treścią: wariant `prompt` — tekst + „Zainstaluj” (wywołuje `prompt()`; wynik `accepted` ukrywa baner, `dismissed` zapisuje zamknięcie) + „×”; wariant `ios` — instrukcja Udostępnij → „Do ekranu początkowego” i informacja o powiadomieniach + „×”. Ma `role="region"` z etykietą, a „×” — `aria-label="Zamknij"`.
- Tylko w `MainPage` (po zalogowaniu): ekran logowania pozostaje czysty, a baner nie zasłania formularza.

### D6. Ikony i metadane

- Źródła: `public/icons/icon.svg` (zaokrąglony kwadrat w kolorze akcentu `#2f7d4f` z białym koszykiem; także favicon) i `public/icons/icon-maskable.svg` (to samo na pełnym tle, znak w strefie bezpiecznej 80%). PNG generuje `scripts/generate-icons.sh` (Firefox w trybie headless robi zrzut SVG w zadanym rozmiarze; brak `rsvg`/ImageMagick w środowisku, a nie chcemy nowej zależności npm tylko do grafiki): `icon-192.png`, `icon-512.png` (`any`), `icon-maskable-512.png` (`maskable`), `apple-touch-icon.png` 180 px (pełne tło — iOS sam zaokrągla rogi). PNG są w repozytorium; skrypt uruchamia się ręcznie po zmianie SVG.
- Manifest `public/manifest.webmanifest`: `name`/`short_name` „Kupto”, `lang: pl`, `start_url: "/"`, `scope: "/"`, `display: standalone`, `background_color: #f6f7f4` (`--bg`), `theme_color: #ffffff` (`--surface`, kolor nagłówka). W `index.html` dodatkowo `<meta name="theme-color">` dla jasnego (`#ffffff`) i ciemnego (`#1d2320`) motywu, `apple-touch-icon` i `apple-mobile-web-app-title`. `viewport-fit=cover` celowo pominięte (układ nie obsługuje wcięć ekranu).

## Risks / Trade-offs

- [Przeładowanie przy przejściu w tło po aktualizacji gubi stan widoku (wybrana zakładka, niewysłany tekst w polu czatu)] → zdarza się tylko po wdrożeniu i tylko gdy użytkownik i tak opuścił aplikację; dane są na serwerze. Akceptowalne w zamian za brak okna „odśwież”.
- [Trwający strumień czatu przerwany przeładowaniem w tle] → wymaga zbiegu wdrożenia i opuszczenia aplikacji w trakcie odpowiedzi; po powrocie historia jest pobierana z serwera, a w najgorszym razie trzeba ponowić wiadomość.
- [Limit 3 s dla HTML przy wolnej sieci pokaże starą powłokę, gdy nowa jest już wdrożona] → stara powłoka działa z API (zmiany API są wstecznie zgodne), a nowy SW zainstaluje się w tle i podmieni wersję przy następnym przejściu w tło.
- [Testy jsdom nie uruchomią prawdziwego SW ani okna instalacji] → logika w czystych funkcjach z testami; działanie zbudowanej aplikacji (nagłówki, rejestracja SW, cache, manifest) sprawdzane ręcznie przez `vite preview`/kontener nginx; instalacja na prawdziwych telefonach — ręcznie po wdrożeniu.
- [Zrzut ekranu Firefoksa jako rasteryzator ikon] → wynik sprawdzany wizualnie; PNG są w repozytorium, więc build i CI nie zależą od Firefoksa.

## Migration Plan

Zmiana addytywna, tylko frontend. Po wdrożeniu przeglądarki zarejestrują SW przy pierwszym otwarciu. Wycofanie — patrz D3.

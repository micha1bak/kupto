# Kupto — frontend

SPA w React + Vite + TypeScript. Dane z serwera pobiera TanStack Query, a odpowiedzi asystenta
są czytane jako strumień SSE (`fetch` + `ReadableStream`). Lista odświeża się na żywo: `EventSource`
na `/api/list/events` dostaje sygnał o zmianie i wtedy lista jest pobierana ponownie
(`src/api/listEvents.ts`); gdy strumień nie działa, lista jest odpytywana co 30 s.

## Uruchomienie deweloperskie

Wymagania: Node.js 22+ oraz działający backend na `localhost:8000` (patrz `backend/README.md`).

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, żądania /api są przekazywane do localhost:8000
```

## Testy i build

```bash
npm test           # Vitest + Testing Library
npm run build      # sprawdzenie typów (tsc) + build produkcyjny do dist/
```

## Struktura

| Katalog | Zawartość |
|---|---|
| `src/api/` | klient HTTP, typy API, hooki zapytań, parser SSE |
| `src/auth/` | logowanie i rejestracja |
| `src/household/` | tworzenie gospodarstwa i zarządzanie członkami |
| `src/list/` | lista zakupów pogrupowana po kategoriach |
| `src/chat/` | czat z asystentem |
| `src/layout/` | układ główny: zakładki na telefonie, dwie kolumny od 900 px, baner instalacji |
| `src/pwa/` | service worker, jego rejestracja i aktualizacje, logika banera, wtyczka Vite budująca `sw.js` |

## PWA

Aplikację można zainstalować na telefonie (manifest `public/manifest.webmanifest`, ikony w `public/icons/`).

- **Service worker** (`src/pwa/sw.ts`) działa tylko w buildzie produkcyjnym. Wtyczka `src/pwa/swPlugin.ts`
  buduje go do `dist/sw.js` z listą plików powłoki (HTML, `assets/`, manifest, ikony) i wersją buildu.
  Pliki powłoki idą z cache tej wersji, dokument HTML najpierw z sieci (po 3 s bez odpowiedzi — z cache).
  **`/api/*` nigdy nie przechodzi przez cache** — SW w ogóle nie obsługuje tych żądań.
- **Aktualizacje**: każdy build zmienia `sw.js` (serwowany z `no-cache`), więc przeglądarka instaluje nową
  wersję przy otwarciu aplikacji, a `src/pwa/register.ts` sprawdza ją też przy powrocie aplikacji z tła.
  Nowy SW od razu przejmuje stronę i usuwa stare cache; strona, która działała na starej wersji,
  przeładowuje się przy najbliższym przejściu w tło.
- **Ikony**: źródłem są `public/icons/icon.svg` i `icon-maskable.svg`; PNG generuje
  `scripts/generate-icons.sh` (Firefox headless + Python z Pillow) — uruchamiać po zmianie SVG.

W produkcji SPA serwuje nginx (`nginx.conf`), który przekazuje `/api` do backendu bez
buforowania, więc odpowiedzi czatu przychodzą strumieniowo.

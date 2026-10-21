# Kupto — frontend

SPA w React + Vite + TypeScript. Dane z serwera pobiera TanStack Query (lista odświeżana co 5 s),
a odpowiedzi asystenta są czytane jako strumień SSE (`fetch` + `ReadableStream`).

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
| `src/layout/` | układ główny: zakładki na telefonie, dwie kolumny od 900 px |

W produkcji SPA serwuje nginx (`nginx.conf`), który przekazuje `/api` do backendu bez
buforowania, więc odpowiedzi czatu przychodzą strumieniowo.

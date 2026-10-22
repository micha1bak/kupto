# Tasks

## 1. Backend (spec: shopping-list — Przeglądanie historii zakupów, Wyszukiwanie produktu w historii)

- [x] 1.1 Moduł `kupto.history` — serwis odczytu zakończeń z paginacją kursorem i wyszukiwania produktu (design D2–D4), schematy odpowiedzi, router `/api/history` zarejestrowany w `main.py` (D1); weryfikacja: `uv run pytest`
- [x] 1.2 Testy API: kolejność i szczegóły zakończenia (sumy ilości, zgłaszający, kupujący, grupy kategorii), paginacja bez powtórzeń i pominięć, obcy kursor, pusta historia, izolacja gospodarstw, wyszukiwanie (wielkość liter, polskie znaki, ostatni zakup, liczba zakupów, brak wyników, izolacja, pusta fraza, znaki `%`/`_`)

## 2. Frontend (spec: shopping-list)

- [x] 2.1 Strona `HistoryPage` (`/history`) z sekcjami zakończeń, grupami kategorii, wyszukiwaniem i „Pokaż więcej”; link „Historia” w `MainPage`, trasa w `App.tsx` (design D5); weryfikacja: testy Vitest, `npx tsc -b`, `npx vite build`

## 3. Integracja

- [x] 3.1 Kroki CI lokalnie: `uv sync --locked`, `uv run ruff check src tests evals`, `uv run ruff format --check src tests evals`, `uv run pytest`; frontend `npm ci`, `npx tsc -b`, `npm test`, `npx vite build`

## Workflow follow-up

- Po scaleniu PR zarchiwizować change (`/opsx:archive`), co doda oba wymagania do `openspec/specs/shopping-list/spec.md`.

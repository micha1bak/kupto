# Tasks

## 1. Backend (spec: shopping-list — Podpowiedzi zwykle kupowanych produktów)

- [ ] 1.1 Heurystyka `usual_missing(session, household, now)` w `kupto/history/usual.py` (design D1, D2)
- [ ] 1.2 Endpoint `GET /api/history/usual` ze schematem odpowiedzi (D3)
- [ ] 1.3 Testy: heurystyka na przygotowanej historii (próg zaległości, porzucone produkty, typowa ilość, mediana), pomijanie produktów na liście, zimny start, izolacja gospodarstw, API (401/409)

## 2. Czat (spec: needs-chat — Podpowiedzi zwykłych produktów w czacie)

- [ ] 2.1 Narzędzie `get_usual_missing` (tylko odczyt) i zasada w prompcie (D4); testy narzędzia
- [ ] 2.2 Ewaluacja: pytanie „czego nam zwykle brakuje?” → propozycja bez zmiany listy, potwierdzenie → dodanie z typową ilością

## 3. Frontend (spec: shopping-list)

- [ ] 3.1 Komponent `UsualSuggestions` (dodanie jednym kliknięciem, ukrycie na dziś) wpięty w `ListView.tsx` (D5); testy Vitest

## 4. Integracja

- [ ] 4.1 Kroki CI lokalnie: backend `uv sync --locked`, `ruff check`, `ruff format --check`, `pytest`; frontend `npm ci`, `npx tsc -b`, `npm test`, `npx vite build`

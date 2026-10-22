# Tasks

## 1. Backend (spec: needs-chat)

- [x] 1.1 Limit wiadomości 8000 znaków w `chat/router.py` (D3); testy: 422 dla 8001 znaków, przyjęcie długiej wiadomości
- [x] 1.2 Zasada 4a w `chat/prompt.py` (D1, D2); test, że instrukcje zawierają zasadę przepisu
- [x] 1.3 Test API z `FakeLLMClient`: propozycja bez zmiany listy, potwierdzenie → zapotrzebowania z notatką „na: <danie>”

## 2. Ewaluacje (spec: needs-chat — Lista zakupów z przepisu)

- [x] 2.1 Wklejony przepis → propozycja składników bez zmiany listy, bez wody i soli
- [x] 2.2 „Brakuje mi tylko …” / „… mam, resztę dodaj” → tylko brakujące składniki z notatką „na: <danie>”

## 3. Frontend

- [x] 3.1 `MAX_LENGTH` 8000 w `ChatView.tsx`, podpowiedź o przepisie w pustym czacie; testy Vitest

## 4. Integracja

- [x] 4.1 Kroki CI lokalnie: backend `uv sync --locked`, `ruff check`, `ruff format --check`, `pytest`; frontend `npm ci`, `npx tsc -b`, `npm test`, `npx vite build`

# Tasks

## 1. Instrukcja systemowa (spec: needs-chat — Odpowiedź po wykonanej akcji)

- [x] 1.1 Zasada 7 (co zrobiono, bez pytania zamykającego, wyjątki), zasada 1 bez oferty pomocy, zwięźlejsze 2, 6, 9 (D1, D2); test w `tests/test_chat_prompt.py`

## 2. Ewaluacje (spec: needs-chat — Odpowiedź po wykonanej akcji)

- [x] 2.1 `assert_no_closing_question` w scenariuszach akcji; w scenariuszach potwierdzeń stan bez zmian przed zgodą (D3) (dopisane; przebieg `-m llm` do wykonania przed merge)

## 3. Integracja

- [x] 3.1 Kroki CI lokalnie: backend `uv sync --locked`, `ruff check`, `ruff format --check`, `pytest`; frontend `npm ci`, `npx tsc -b`, `npm test`, `npx vite build`

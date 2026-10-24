# Tasks

## 1. Instrukcja systemowa (spec: needs-chat — Odpowiedź po wykonanej akcji)

- [x] 1.1 Zasada 7 (co zrobiono, bez pytania zamykającego, wyjątki), zasady 1 i 9 bez zachęt do pytań, zwięźlejsze 2, 6, 8 (D1, D2); test w `tests/test_chat_prompt.py`

## 2. Ewaluacje (spec: needs-chat — Odpowiedź po wykonanej akcji)

- [x] 2.1 `assert_no_closing_question` w scenariuszach akcji i `"?"` w scenariuszach potwierdzeń (D3) (dopisane; przebieg `-m llm` do wykonania przed merge)

## 3. Integracja

- [x] 3.1 Kroki CI lokalnie: backend `uv sync --locked`, `ruff check`, `ruff format --check`, `pytest`; frontend `npm ci`, `npx tsc -b`, `npm test`, `npx vite build`

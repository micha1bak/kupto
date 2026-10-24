# Tasks

## 1. Model danych (D1, D2, D3, D8, D11)

- [x] 1.1 `User.name`, `User.chat_hidden_before`, `ChatMessage.private`, indeks `(household_id, created_at)`; migracja `0012` z `down_revision = "0011"`
- [x] 1.2 `tests/test_migrations.py`: upgrade z 0011 na danych (archiwum `private = true`, domyślne wartości nowych wierszy), downgrade, ponowny upgrade

## 2. Imię (spec: user-accounts)

- [x] 2.1 `POST /api/auth/register` wymaga `name`; `PATCH /api/users/me`; `name` w profilu; `display_name` (D3, D4); testy API
- [x] 2.2 Powiadomienia push z imieniem (D4); test

## 3. Czat grupowy (spec: needs-chat)

- [x] 3.1 `GET /api/chat/messages`: wątek gospodarstwa bez archiwum, autor, `mine`, limit 200, ukrycie u siebie; `DELETE` ustawia `chat_hidden_before` (D1, D8); testy API
- [x] 3.2 Kontekst modelu: historia gospodarstwa z imionami, okno 24 h, imiona w liście JSON, instrukcja z autorem ostatniej wiadomości i zasadą potwierdzeń (D5, D6); testy promptu i API (potwierdzenie zakończenia zakupów tylko od autora)
- [x] 3.3 Sygnał `chat_changed`: rodzaj `chat` w `lists/events.py`, zdarzenie w `/api/list/events`, publikacja przy zapisie wiadomości i odpowiedzi (D9); testy brokera i strumienia

## 4. Frontend

- [x] 4.1 Pole „Imię” w rejestracji; blokujący ekran uzupełnienia imienia; edycja imienia na profilu (D3); testy Vitest
- [x] 4.2 `ChatView`: dymki z imieniem, godziną, oznaczeniem asystenta; odświeżanie na `chat_changed` (D9, D10); `ChatOptions`: „Ukryj historię u siebie” (D8); `chatTitle` (D10); testy Vitest i `viewport.test.ts`

## 5. Ewaluacje (spec: needs-chat — Czat grupowy gospodarstwa, Potwierdzenia w czacie grupowym)

- [x] 5.1 Scenariusze `-m llm`: kontekst wiadomości innego domownika, „tak” od innej osoby nie potwierdza propozycji (dopisane; przebieg do wykonania przed merge — limit Groq wyczerpany)

## 6. Integracja

- [x] 6.1 Kroki CI lokalnie: backend `uv sync --locked`, `ruff check`, `ruff format --check`, `pytest`; frontend `npm ci`, `npx tsc -b`, `npm test`, `npx vite build`

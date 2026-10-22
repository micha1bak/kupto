# Tasks

## 1. Porządki i szkielet projektu

- [x] 1.1 Usunąć aplikację TypeScript (`src/`, `prisma/`, `prisma.config.ts`, `package.json`, `package-lock.json`, `tsconfig.json`, `jest.config.js`, `api.json`, stary `Dockerfile`, `.dockerignore`); weryfikacja: `git ls-files` nie zawiera tych ścieżek
- [x] 1.2 Zawęzić w `.gitignore` regułę `*.md`, aby śledzone były `README.md` i dokumentacja w `backend/`/`frontend/`, oraz dodać wpisy Pythona i Node (`.venv`, `__pycache__`, `.pytest_cache`, `frontend/node_modules`, `frontend/dist`); weryfikacja: `git check-ignore README.md` nic nie zwraca, a `git check-ignore frontend/dist/x` zwraca regułę
- [x] 1.3 Utworzyć `backend/` z `pyproject.toml` (uv, Python 3.12; FastAPI, uvicorn, SQLAlchemy[asyncio], asyncpg, alembic, pydantic-settings, PyJWT, pwdlib[argon2], openai; dev: pytest, pytest-asyncio, httpx, testcontainers[postgres], ruff) i pakietem `kupto`; weryfikacja: `uv sync` kończy się sukcesem
- [x] 1.4 Dodać `kupto.config` (pydantic-settings: `DATABASE_URL`, `JWT_SECRET`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `CHAT_RATE_LIMIT_PER_HOUR`, `CHAT_HISTORY_LIMIT`, `CHAT_MAX_TOOL_ROUNDS`, `COOKIE_SECURE`) oraz aplikację FastAPI z `GET /api/health`; weryfikacja: test pytest dla `/api/health` przechodzi
- [x] 1.5 Utworzyć `frontend/` (Vite + React + TypeScript, React Router, TanStack Query, Vitest + Testing Library) z proxy `/api` do `localhost:8000` w `vite.config.ts`; weryfikacja: `npm run build` i `npm test` przechodzą

## 2. Baza danych

- [x] 2.1 Zdefiniować modele SQLAlchemy z design D3 (`users`, `households`, `shopping_lists`, `list_items`, `needs`, `household_products`, `chat_messages`, `chat_pending_actions`) wraz z enumami kategorii i jednostek oraz indeksami (unique `list_id, normalized_name`; `chat_messages(user_id, created_at)`); weryfikacja: `ruff check` przechodzi
- [x] 2.2 Skonfigurować Alembic (async) i wygenerować migrację początkową; weryfikacja: `alembic upgrade head` i `alembic downgrade base` działają na pustym Postgresie z testcontainers
- [x] 2.3 Przygotować fixtures pytest (kontener Postgres na sesję testów, migracje, czyszczenie tabel (TRUNCATE) po każdym teście — narzędzia czatu commitują własne transakcje, `AsyncClient`, fabryki użytkowników i gospodarstw); weryfikacja: test dymny tworzący użytkownika przechodzi

## 3. Konta użytkowników (spec: user-accounts)

- [x] 3.1 Zaimplementować hashowanie haseł (argon2) i wydawanie/weryfikację JWT oraz zależność FastAPI `current_user` zwracającą 401 bez ważnej sesji; weryfikacja: testy jednostkowe dla poprawnego, wygasłego i sfałszowanego tokenu
- [x] 3.2 Dodać `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/users/me`; weryfikacja: testy API pokrywają wszystkie scenariusze ze `specs/user-accounts/spec.md` (201/409/422, 200/401 z jednakowym komunikatem, wylogowanie, profil z gospodarstwem i bez)

## 4. Gospodarstwa (spec: households)

- [x] 4.1 Zaimplementować serwis gospodarstw: utworzenie z pustą listą, dodawanie członka po loginie, lista członków, usuwanie członka, opuszczanie z przekazaniem własności i usunięciem ostatniego gospodarstwa; weryfikacja: testy serwisu dla każdej reguły
- [x] 4.2 Dodać endpointy `POST /api/households`, `GET /api/households/me`, `POST /api/households/me/members`, `DELETE /api/households/me/members/{user_id}`, `POST /api/households/me/leave` oraz zależność `current_household` zwracającą 409 dla użytkownika bez gospodarstwa; weryfikacja: testy API pokrywają wszystkie scenariusze ze `specs/households/spec.md` (409, 404, 403, przekazanie własności, kaskadowe usunięcie listy i historii czatu)

## 5. Lista zakupów (spec: shopping-list)

- [x] 5.1 Zaimplementować normalizację nazw i agregację ilości (suma per jednostka liczona przy odczycie); weryfikacja: testy jednostkowe (wielkość liter, białe znaki, różne jednostki, brak ilości)
- [x] 5.2 Zaimplementować serwis listy `kupto.lists.service`: dodanie zapotrzebowań ze scalaniem i pamięcią kategorii (`household_products`), zmiana/wycofanie własnego zapotrzebowania, usunięcie pozycji, oznaczanie/cofanie kupionych z zapisem kto i kiedy, zakończenie zakupów; wszystkie operacje ograniczone do gospodarstwa wywołującego; weryfikacja: testy serwisu dla każdego scenariusza ze `specs/shopping-list/spec.md`
- [x] 5.3 Dodać endpointy REST: `GET /api/list` (pogrupowana po kategoriach), `POST /api/list/needs`, `PATCH`/`DELETE /api/list/needs/{id}`, `DELETE /api/list/items/{id}`, `POST`/`DELETE /api/list/items/{id}/bought`, `POST /api/list/finish`; weryfikacja: testy API, w tym 404 przy próbie dostępu do pozycji innego gospodarstwa

## 6. Czat z asystentem (spec: needs-chat)

- [x] 6.1 Zdefiniować protokół `LLMClient`, implementację `OpenAIResponsesClient` (Responses API, strumieniowanie, `store=false`, timeout) i `FakeLLMClient` ze skryptowanymi tekstami i wywołaniami narzędzi; weryfikacja: test jednostkowy `FakeLLMClient` oraz test mapowania eventów strumienia OpenAI na wewnętrzne eventy (na nagranych przykładach)
- [x] 6.2 Zdefiniować narzędzia z design D6 (ścisłe schematy JSON, enumy kategorii i jednostek) mapowane na serwis listy, z kontekstem użytkownika i gospodarstwa wstrzykiwanym z sesji; weryfikacja: testy pokazują, że narzędzie nie może zmienić pozycji innego gospodarstwa ani cudzego zapotrzebowania przez `update_need`/`withdraw_need`
- [x] 6.3 Zaimplementować mechanizm potwierdzeń `request_finish_shopping`/`confirm_finish_shopping` oparty na `chat_pending_actions` (D7); weryfikacja: testy — potwierdzenie bez wcześniejszego żądania nic nie robi, a każda inna wiadomość kasuje oczekującą akcję
- [x] 6.4 Napisać polski prompt systemowy (zakres, język, mianownik w nazwach, zasada potwierdzania propozycji, odmowa tematów spoza zakupów) i budowę kontekstu (prompt + stan listy + ostatnie `CHAT_HISTORY_LIMIT` wiadomości); weryfikacja: test jednostkowy budowy kontekstu (przycinanie historii, obecność stanu listy)
- [x] 6.5 Zaimplementować pętlę agenta z limitem `CHAT_MAX_TOOL_ROUNDS` i endpoint SSE `POST /api/chat/messages` (eventy `delta`, `list_changed`, `error`, `done`), zapisujący wiadomości do historii; weryfikacja: testy API z `FakeLLMClient` dla dodania produktów, scalenia z istniejącą pozycją i błędu modelu (zmiany sprzed błędu pozostają, event `error`)
- [x] 6.6 Dodać walidację długości (422) i limit wiadomości na godzinę (429 z `Retry-After`) sprawdzane przed wywołaniem modelu; weryfikacja: testy API potwierdzają, że `FakeLLMClient` nie został wywołany
- [x] 6.7 Dodać `GET /api/chat/messages` (historia własna) i `DELETE /api/chat/messages` (wyczyszczenie); weryfikacja: testy — członek B nie widzi historii A, wyczyszczenie nie zmienia listy
- [x] 6.8 Przygotować ewaluacje `backend/evals/` (`@pytest.mark.llm`, domyślnie pomijane) dla scenariuszy zależnych od modelu: wiele produktów w wiadomości, odmiana nazw („dwóch jogurtów naturalnych”), kategoryzacja, dopytywanie o „coś na grilla” i potwierdzenie z wyjątkiem, odmowa tematu spoza zakupów, próba prompt injection, odpowiedź po angielsku; weryfikacja: `uv run pytest -m llm` z prawdziwym kluczem przechodzi, a wynik i wybrany `OPENAI_MODEL` są opisane w `backend/README.md`

## 7. Frontend SPA

- [x] 7.1 Przygotować klienta API (fetch z `credentials: 'include'`, obsługa 401 → przekierowanie do logowania) i ekrany rejestracji oraz logowania; weryfikacja: testy Vitest formularzy (walidacja, komunikat błędu 401/409)
- [x] 7.2 Dodać widok gospodarstwa: utworzenie, lista członków, dodawanie i usuwanie członków (tylko właściciel), opuszczenie; weryfikacja: testy komponentu dla widoku właściciela i zwykłego członka
- [x] 7.3 Dodać widok listy pogrupowanej po kategoriach z odhaczaniem, usuwaniem, ręcznym dodawaniem, zakończeniem zakupów i pollingiem co 5 s; weryfikacja: testy komponentu (render grup, optymistyczne odhaczenie) i ręczne sprawdzenie w dwóch przeglądarkach, że zmiana pojawia się w ciągu 10 s
- [x] 7.4 Dodać widok czatu: parser SSE na `fetch` + `ReadableStream`, przyrostowe wyświetlanie odpowiedzi, odświeżenie listy po `list_changed`, komunikaty 422/429/`error`, wczytanie i czyszczenie historii, informacja o przetwarzaniu wiadomości przez OpenAI; weryfikacja: testy Vitest parsera SSE (fragmenty dzielone w połowie eventu) i komponentu czatu
- [x] 7.5 Dopracować układ mobile-first (zakładki Czat/Lista na telefonie, dwie kolumny na desktopie) i opisać uruchomienie deweloperskie w `frontend/README.md`; weryfikacja: ręczne sprawdzenie przy szerokości 375 px i 1280 px oraz wykonanie kroków z README

## 8. Wdrożenie

- [x] 8.1 Dodać `backend/Dockerfile` (python:3.12-slim + uv; start: `alembic upgrade head` → `uvicorn`) i `frontend/Dockerfile` (build node → nginx z proxy `/api` i `proxy_buffering off`); weryfikacja: `docker build` obu obrazów kończy się sukcesem
- [x] 8.2 Przepisać `docker-compose.yml` (usługi `db` z wolumenem `db_v2`, `backend`, `web` na porcie 3000; Postgres tylko na `127.0.0.1`; poprawny `DATABASE_URL`) i `.env.example` (nowe zmienne OpenAI i czatu); weryfikacja: `docker compose up --build` lokalnie, `curl localhost:3000/api/health` zwraca 200, a odpowiedź czatu w przeglądarce przychodzi strumieniowo przez nginx
- [x] 8.3 Zaktualizować `.github/workflows/deploy.yml` (jeśli potrzeba) i opisać w `README.md` w roocie architekturę, uruchomienie lokalne, zmienne środowiskowe oraz procedurę wdrożenia i rollbacku z design (Migration Plan); weryfikacja: kroki lokalne z README wykonane od zera na czystym klonie

## 9. Weryfikacja end-to-end

- [x] 9.1 Test integracyjny backendu z `FakeLLMClient`: dwóch użytkowników w jednym gospodarstwie zgłasza przez czat „mleko” (1 l i 2 l), lista pokazuje jedną pozycję 3 l z dwoma zgłaszającymi, jeden oznacza ją jako kupioną, drugi kończy zakupy przez czat z potwierdzeniem; weryfikacja: test przechodzi w `uv run pytest`
- [x] 9.2 Ręczny smoke test na lokalnym `docker compose` z prawdziwym kluczem OpenAI według scenariuszy ze specyfikacji `needs-chat`; weryfikacja: wszystkie scenariusze zachowują się zgodnie ze specyfikacją, a odstępstwa są zgłoszone jako poprawki promptu lub zadania

## Workflow follow-up

- Workflow wdrożenia na VPS usunięty (docelowo AWS) — wdrożenie zaplanować jako osobną zmianę OpenSpec; przed wyłączeniem VPS wykonać `pg_dump` starej bazy, jeśli dane mają zostać zachowane.
- Po wdrożeniu i smoke teście na produkcji zarchiwizować change: `/opsx:archive`.

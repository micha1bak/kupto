# Design

## Context

Motywacja i zakres: patrz `proposal.md`. Wymagania: `specs/user-accounts`, `specs/households`, `specs/shopping-list`, `specs/needs-chat`.

Stan obecny, który wpływa na podejście:

- Monolit Express 5 + TypeScript + Prisma 7 na PostgreSQL 18; frontend to statyczne `src/public/` (czysty JS) serwowane przez Express na porcie 3000.
- Uwierzytelnianie: JWT w ciasteczku httpOnly, `SameSite=strict`, ważność 30 dni.
- Deploy: GitHub Actions → SSH na VPS → `git pull` + `docker compose up -d --build` w `/root/kupto`. Postgres działa w tym samym compose na wolumenie `db_prod`, a port 5432 jest wystawiony publicznie.
- `docker-compose.yml` ma literówkę w `DATABASE_URL` (`#{DB_USER}`), a `.gitignore` ignoruje wszystkie pliki `*.md` poza wyjątkami dla OpenSpec.
- Stara aplikacja nie ma żadnej logiki LLM ani specyfikacji, które trzeba zachować.

## Goals / Non-Goals

**Goals:**

- Jeden backend w Pythonie, który egzekwuje autoryzację i reguły listy niezależnie od tego, czy zmianę zleca LLM, czy UI.
- LLM jako warstwa interpretacji: model tylko wybiera i parametryzuje operacje (narzędzia), a stan listy zmienia wyłącznie kod domenowy.
- Deterministyczne testy bez połączenia z OpenAI oraz osobny, ręcznie uruchamiany zestaw ewaluacji z prawdziwym modelem.
- Wdrożenie na tym samym VPS tym samym mechanizmem (`docker compose up -d --build`).

**Non-Goals:**

- Powiadomienia push i aktualizacje w czasie rzeczywistym przez WebSocket (wystarczy polling, patrz D10).
- Historia zakończonych zakupów, szablony list, przepisy i planowanie posiłków.
- Wiele gospodarstw na użytkownika, zaproszenia z akceptacją, role inne niż właściciel/członek.
- Aplikacja mobilna natywna (SPA ma być responsywna, mobile-first).
- Migracja danych ze starej bazy.

## Decisions

### D1. Struktura repozytorium: `backend/` + `frontend/`

Kod TypeScript zostaje usunięty z roota; powstają `backend/` (pakiet Python `kupto`) i `frontend/` (SPA). Konfiguracja wdrożenia (`docker-compose.yml`, `.env.example`, workflow) zostaje w roocie.
*Alternatywa:* osobne repozytoria — odrzucone, bo deploy przez jeden `git pull` i jeden compose jest prostszy.

### D2. Backend: Python 3.12, FastAPI, Pydantic v2, uv

FastAPI daje asynchroniczność (ważną przy długich wywołaniach LLM i strumieniowaniu), walidację przez Pydantic (kody 422 zgodne ze specyfikacją) i automatyczną dokumentację OpenAPI (zastępuje ręczny `api.json`). Zależnościami i lockfile'em zarządza `uv`.
*Alternatywy:* Django + DRF (cięższe, synchroniczne ORM, panel admina zbędny), Flask (brak natywnej asynchroniczności i walidacji).

### D3. Dane: PostgreSQL + SQLAlchemy 2.0 (async, asyncpg) + Alembic

Model danych:

| Tabela | Najważniejsze kolumny |
|---|---|
| `users` | `id`, `login` (unique), `password_hash`, `household_id` (nullable FK), `joined_household_at` |
| `households` | `id`, `name`, `owner_id` (FK users) |
| `shopping_lists` | `id`, `household_id` (unique FK) |
| `list_items` | `id`, `list_id`, `name`, `normalized_name`, `category` (enum), `bought_at`, `bought_by_id`; unique(`list_id`, `normalized_name`) |
| `needs` | `id`, `item_id` (FK, cascade), `user_id` (nullable, set null), `amount` (numeric, nullable), `unit` (enum, nullable), `note`, `created_at` |
| `household_products` | `household_id`, `normalized_name`, `category` — pamięć kategorii (wymaganie „Ręczne dodanie pozycji”) |
| `chat_messages` | `id`, `user_id`, `household_id` (FK, cascade — historia znika razem z gospodarstwem), `role`, `content`, `created_at` |
| `chat_pending_actions` | `user_id` (PK), `action`, `created_at` — oczekujące potwierdzenia (D7) |

Przynależność to kolumna `users.household_id`, bo użytkownik należy do co najwyżej jednego gospodarstwa — nie trzeba tabeli łączącej. Ilości łącznie liczy się przy odczycie (suma `amount` grupowana po `unit`), więc wycofanie zapotrzebowania niczego nie musi przeliczać. Normalizacja nazwy: NFC → trim → zredukowanie wewnętrznych białych znaków → lowercase. Jednostki należą do zamkniętego zbioru: `szt`, `kg`, `g`, `l`, `ml`, `opak`.
*Alternatywy:* SQLModel (mniej dojrzałe przy async i migracjach), przechowywanie zsumowanej ilości w `list_items` (wymaga przeliczania przy każdej zmianie).

### D4. Uwierzytelnianie: JWT w ciasteczku httpOnly

PyJWT (HS256, sekret `JWT_SECRET`), ciasteczko `httpOnly`, `SameSite=Strict`, `Secure` poza trybem deweloperskim, ważne 30 dni; hasła hashowane przez argon2 (`pwdlib`). Frontend i API działają w tym samym originie (D11), więc `SameSite=Strict` wystarcza jako ochrona przed CSRF.
*Alternatywa:* sesje po stronie serwera — dają unieważnianie sesji, ale zachowujemy model znany z obecnej aplikacji. Ryzyko opisano niżej.

### D5. LLM: OpenAI Python SDK, Responses API z narzędziami (function calling)

Klient `openai` (async), Responses API z narzędziami o ścisłych schematach JSON (`strict: true`) i `store=false` — stan rozmowy trzymamy sami w `chat_messages`. Model ustawia `OPENAI_MODEL` w konfiguracji. Wywołania LLM są ukryte za protokołem `LLMClient` w `kupto.chat.llm`, dzięki czemu w testach można podstawić `FakeLLMClient` ze skryptowanymi odpowiedziami i wywołaniami narzędzi.
*Alternatywy:* Chat Completions API (starsze, ale też wystarczające — przejście jest proste dzięki `LLMClient`), LangChain/PydanticAI (dodatkowa warstwa bez wyraźnej korzyści przy kilku narzędziach).

### D6. Pętla agenta i narzędzia

Narzędzia przekazywane modelowi (każde wykonywane w kontekście `user_id` i `household_id` z sesji, nigdy z argumentów modelu):

- `get_list()` — aktualna lista,
- `add_needs(items: [{name, amount?, unit?, note?, category}])` — `name` w mianowniku po polsku, `category` z enumu,
- `update_need(item_id, amount?, unit?, note?)` / `withdraw_need(item_id)` — tylko własne zapotrzebowania autora,
- `remove_item(item_id)`, `mark_bought(item_ids)`, `unmark_bought(item_ids)`,
- `request_finish_shopping()` / `confirm_finish_shopping()` — patrz D7.

Pętla: wywołanie modelu → wykonanie narzędzi → zwrócenie wyników do modelu, maksymalnie 5 rund (`CHAT_MAX_TOOL_ROUNDS`), potem odpowiedź końcowa. Narzędzia wywołują te same serwisy domenowe (`kupto.lists.service`) co endpointy REST, więc reguły scalania, kategorii i autoryzacji istnieją w jednym miejscu. Kontekst modelu: polski prompt systemowy (zakres, język, zasada potwierdzania propozycji) + bieżący stan listy + ostatnie 20 wiadomości (`CHAT_HISTORY_LIMIT`). W historii zapisujemy tylko tekst użytkownika i asystenta; wyniki narzędzi nie są utrwalane, bo aktualny stan listy i tak trafia do kontekstu.

### D7. Potwierdzenia: zakończenie zakupów egzekwowane po stronie serwera

Zakończenie zakupów jest destrukcyjne, więc nie polegamy tylko na prompcie. `request_finish_shopping` zapisuje oczekującą akcję w `chat_pending_actions`. `confirm_finish_shopping` działa tylko wtedy, gdy taka akcja istnieje i powstała w poprzedniej turze; każda inna wiadomość ją kasuje. Potwierdzanie propozycji przy niejasnych potrzebach („coś na grilla”) zapewnia już tylko prompt, bo dodanie pozycji łatwo cofnąć — sprawdzają to ewaluacje (D12).

### D8. Strumieniowanie: SSE z endpointu POST

`POST /api/chat/messages` zwraca `text/event-stream` z eventami `delta` (fragment tekstu), `list_changed` (lista się zmieniła — frontend od razu odświeża widok), `error` i `done`. Frontend czyta strumień przez `fetch` + `ReadableStream` (`EventSource` nie obsługuje POST). Walidacja długości i limit liczby wiadomości są sprawdzane przed otwarciem strumienia, więc zwracają zwykłe kody 422/429. Błąd modelu w trakcie strumienia daje event `error`, a zmiany już zapisane w bazie zostają (każde narzędzie commituje własną transakcję).
*Alternatywa:* WebSocket — więcej infrastruktury (proxy, reconnect) bez korzyści dla modelu żądanie–odpowiedź.

### D9. Limit wiadomości bez dodatkowej infrastruktury

Limit liczony jest zapytaniem o liczbę wiadomości `role=user` danego użytkownika w ostatnich 60 minutach (indeks na `user_id, created_at`). Domyślnie 30/h, konfigurowalne przez `CHAT_RATE_LIMIT_PER_HOUR`. `Retry-After` wynika z czasu najstarszej wiadomości w oknie.
*Alternatywa:* Redis — zbędny przy jednej instancji backendu.

### D10. Frontend: React + Vite + TypeScript, TanStack Query

SPA w `frontend/`: React Router (logowanie/rejestracja, gospodarstwo, główny widok czat + lista), TanStack Query do danych serwerowych z pollingiem listy co 5 s (spełnia wymaganie „Widoczność zmian” ≤ 10 s) oraz natychmiastowym odświeżeniem po evencie `list_changed`. Testy: Vitest + Testing Library. Układ mobile-first: na telefonie zakładki Czat/Lista, na desktopie dwie kolumny. Style: zwykły CSS (CSS Modules), bez frameworka UI.
*Alternatywy:* Vue/Svelte (równie dobre — React wybrany ze względu na ekosystem), WebSocket zamiast pollingu (non-goal).

### D11. Wdrożenie: trzy kontenery, wspólny origin przez nginx

`docker-compose.yml`: `db` (postgres:18.1, nowy wolumen `db_v2`), `backend` (python:3.12-slim + uv; przy starcie `alembic upgrade head`, potem `uvicorn`), `web` (wieloetapowy build: node build → nginx serwujący `dist/` i proxy `/api` do backendu z `proxy_buffering off` dla SSE). Publicznie wystawiony jest tylko `web` na porcie 3000, tak jak dziś. Postgres nie jest już wystawiony publicznie — dostęp deweloperski przez `127.0.0.1:5432` i tunel SSH. Nowe zmienne: `OPENAI_API_KEY`, `OPENAI_MODEL`, `CHAT_RATE_LIMIT_PER_HOUR`; `DATABASE_URL` budowana poprawnie (bez literówki `#{`).

### D12. Testy

- Backend: pytest + pytest-asyncio + httpx `AsyncClient`, prawdziwy PostgreSQL z testcontainers (zgodność z produkcją, m.in. enumy i unikalności), `FakeLLMClient` w testach czatu.
- Ewaluacje LLM: `backend/evals/` z markerem `@pytest.mark.llm`, pomijane domyślnie i uruchamiane ręcznie z kluczem API. Sprawdzają scenariusze specyfikacji zależne od modelu: odmiana nazw, kategoryzacja, dopytywanie, odmowa tematów spoza zakupów, odporność na prompt injection.
- Frontend: Vitest dla komponentów czatu (parsowanie SSE) i listy.

## Risks / Trade-offs

- [Model źle zinterpretuje potrzebę albo kategorię] → ścisłe schematy narzędzi, enum kategorii i jednostek, odpowiedź zawsze wymienia wprowadzone zmiany, każdą zmianę można cofnąć ręcznie w UI, ewaluacje przed wdrożeniem.
- [Model doda pozycje mimo braku potwierdzenia propozycji] → reguła w prompcie + ewaluacje; operacja odwracalna. Operacja nieodwracalna (zakończenie zakupów) jest chroniona po stronie serwera (D7).
- [Prompt injection] → narzędzia dostają kontekst gospodarstwa z sesji, a nie z argumentów; model nie ma dostępu do SQL ani do danych innych gospodarstw, więc nawet „przejęty” model może zmienić tylko listę autora.
- [Koszty OpenAI] → limit 2000 znaków, limit wiadomości na godzinę, przycinanie historii do 20 wiadomości, maksymalnie 5 rund narzędzi, konfigurowalny (tańszy) model.
- [Prywatność: treści rozmów trafiają do OpenAI] → `store=false`, informacja w UI czatu, brak danych osobowych w prompcie poza loginem.
- [JWT bez unieważniania po stronie serwera] → po usunięciu z gospodarstwa dostęp jest i tak sprawdzany przy każdym żądaniu na podstawie bazy (`users.household_id`), a nie tokenu. Skradziony token pozostaje ważny do wygaśnięcia — akceptowane na tym etapie.
- [Polling co 5 s generuje ruch] → lekkie zapytanie, mała skala gospodarstw domowych; ewentualne przejście na SSE/WebSocket później bez zmiany specyfikacji.
- [Utrata starych danych] → zgodnie z decyzją brak migracji; przed wdrożeniem wykonujemy `pg_dump`, a stary wolumen `db_prod` zostaje nietknięty.

## Migration Plan

1. Przed wdrożeniem na VPS: `pg_dump` starej bazy do pliku poza repozytorium.
2. Dodać do `.env` na VPS `OPENAI_API_KEY`, `OPENAI_MODEL` i nowe zmienne z `.env.example`.
3. Merge do `main` → workflow wykonuje `git pull` i `docker compose up -d --build`; backend przy starcie tworzy schemat migracjami Alembic na nowym wolumenie `db_v2`.
4. Smoke test: rejestracja, utworzenie gospodarstwa, wiadomość w czacie, odhaczenie pozycji.
5. Rollback: `git revert` merge'a (lub checkout poprzedniego commita na VPS) i `docker compose up -d --build` — stara konfiguracja używa nietkniętego wolumenu `db_prod`. Zbędny stary wolumen usuwamy ręcznie po okresie stabilizacji.

## Open Questions

- Domyślna wartość `OPENAI_MODEL` (koszt vs jakość) — do wybrania na podstawie wyników ewaluacji; konfiguracja tego nie zmienia.
- Szczegóły wizualne UI (kolorystyka, ikony) — do ustalenia przy implementacji frontendu.

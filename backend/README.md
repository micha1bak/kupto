# Kupto — backend

FastAPI + SQLAlchemy 2 (async) + Alembic na PostgreSQL. Asystent korzysta z OpenAI Responses API
(lub zgodnego dostawcy, np. Groq) z narzędziami (function calling): model wybiera operacje, a stan listy zmienia wyłącznie
`kupto.lists.service`.

## Uruchomienie deweloperskie

Wymagania: [uv](https://docs.astral.sh/uv/) i Docker (Postgres oraz testy).

```bash
cd backend
uv sync
docker run -d --name kupto-pg -e POSTGRES_USER=kupto -e POSTGRES_PASSWORD=kupto \
  -e POSTGRES_DB=kupto -p 127.0.0.1:55432:5432 postgres:18.1
cat > .env <<'ENV'
DATABASE_URL=postgresql+asyncpg://kupto:kupto@127.0.0.1:55432/kupto
JWT_SECRET=dev-secret-change-me-0123456789abcdef
COOKIE_SECURE=false
OPENAI_API_KEY=sk-...
ENV
uv run alembic upgrade head
uv run uvicorn kupto.main:app --reload    # http://localhost:8000, dokumentacja: /api/docs
```

## Konfiguracja

| Zmienna | Domyślnie | Opis |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://kupto:kupto@localhost:5432/kupto` | połączenie z bazą |
| `JWT_SECRET` | — (wymagane w produkcji) | sekret podpisu sesji |
| `COOKIE_SECURE` | `true` | ciasteczko sesji tylko przez HTTPS |
| `OPENAI_API_KEY` | — | klucz dostawcy modelu |
| `OPENAI_BASE_URL` | — (OpenAI) | adres dostawcy zgodnego z Responses API, np. `https://api.groq.com/openai/v1` |
| `OPENAI_MODEL` | `gpt-4.1-mini` | model asystenta |
| `CHAT_RATE_LIMIT_PER_HOUR` | `30` | limit wiadomości na użytkownika |
| `CHAT_HISTORY_LIMIT` | `20` | ile ostatnich wiadomości trafia do modelu |
| `CHAT_MAX_TOOL_ROUNDS` | `5` | maks. rund wywołań narzędzi na wiadomość |

## Testy

```bash
uv run pytest               # testy (Postgres w testcontainers, model zastąpiony FakeLLMClient)
uv run ruff check src tests evals
```

## Ewaluacje asystenta (prawdziwy model)

`evals/` sprawdza scenariusze ze specyfikacji `needs-chat`, które zależą od modelu: rozpoznawanie
wielu produktów, mianownik nazw, ilości i notatki, dopytywanie przy ogólnych potrzebach, odmowę
tematów spoza zakupów, odporność na prompt injection, oznaczanie kupionych, potwierdzanie
zakończenia zakupów i język odpowiedzi. Domyślnie są pomijane (marker `llm`).

```bash
OPENAI_API_KEY=sk-... OPENAI_MODEL=gpt-4.1-mini uv run pytest -m llm
```

Ustawienia można też wpisać do `backend/.env`. Przy dostawcy z niskim limitem tokenów na minutę
(np. darmowy plan Groq) ustaw odstęp między wiadomościami, np. `EVAL_DELAY_SECONDS=45`
(pełne uruchomienie trwa wtedy ok. 10 minut).

### Wyniki (2026-10-21, Groq `openai/gpt-oss-120b`, `EVAL_DELAY_SECONDS=45`)

| Przebieg | Wynik | Uwagi |
|---|---|---|
| 1 | 8/11 | model nie wiedział, że już poprosił o potwierdzenie zakończenia zakupów; odpowiedź po polsku na wiadomość po angielsku; zbyt ścisła asercja jednostki |
| 2 (po poprawkach) | 9/11 | „tak, ale bez kiełbasy” potraktowane jak nowa prośba (niestabilne); zbyt ścisła asercja odmiany nazwy |
| 3–4 (dwa poprawiane scenariusze) | 4/4 zachowań zgodnych ze spec | „grill” poprawny 3× z rzędu po doprecyzowaniu reguły potwierdzeń |

Wnioski po przebiegach:

- Stan oczekującego potwierdzenia jest przekazywany modelowi w instrukcjach (historia zawiera
  tylko tekst, więc model sam go nie widzi).
- Model bywa niedeterministyczny w dopytywaniu i potwierdzaniu propozycji — przy zmianach
  promptu uruchamiaj ewaluacje kilkukrotnie.
- Darmowy plan Groq (ok. 8 tys. tokenów/min, 200 tys./dzień) wystarcza na ok. 3 pełne
  przebiegi dziennie; bez `EVAL_DELAY_SECONDS` testy trafiają na limit 429.

## Struktura

| Moduł | Zawartość |
|---|---|
| `kupto/auth/` | hasła (argon2), sesje JWT w ciasteczku, endpointy `/api/auth/*`, `/api/users/me` |
| `kupto/households/` | gospodarstwa i członkowie |
| `kupto/lists/` | reguły listy (scalanie, kategorie, kupione) i endpointy `/api/list/*` |
| `kupto/chat/` | klient LLM, narzędzia, prompt, pętla agenta, endpoint SSE `/api/chat/messages` |
| `migrations/` | migracje Alembic |

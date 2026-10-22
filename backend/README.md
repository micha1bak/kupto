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
uv run uvicorn --factory kupto.main:create_app --reload    # http://localhost:8000, dokumentacja: /api/docs
```

## Konfiguracja

| Zmienna | Domyślnie | Opis |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://kupto:kupto@localhost:5432/kupto` | połączenie z bazą |
| `JWT_SECRET` | — (wymagane, min. 32 znaki) | sekret podpisu sesji; bez niego aplikacja nie wystartuje |
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
wielu produktów, mianownik nazw, kategoryzację, ilości i notatki, dopytywanie przy ogólnych
potrzebach („coś na grilla”) i potwierdzenie z wyjątkiem, odmowę tematów spoza zakupów, odporność
na prompt injection, oznaczanie kupionych, potwierdzanie zakończenia zakupów i język odpowiedzi
(12 testów). Domyślnie są pomijane (marker `llm`).

```bash
OPENAI_API_KEY=gsk_... OPENAI_BASE_URL=https://api.groq.com/openai/v1 \
  OPENAI_MODEL=openai/gpt-oss-120b EVAL_DELAY_SECONDS=40 uv run pytest -m llm
```

Ustawienia można też wpisać do `backend/.env`. Przy dostawcy z niskim limitem tokenów na minutę
(np. darmowy plan Groq) ustaw odstęp między wiadomościami, np. `EVAL_DELAY_SECONDS=40`
(pełne uruchomienie trwa wtedy ok. 9 minut).

### Wybór modelu (2026-10-22, Groq, `EVAL_DELAY_SECONDS=40`, prompt bez zmian)

| Model | Przebieg 1 | Przebieg 2 | Błędy | Cena wej./wyj. za 1 mln tokenów | Koszt przebiegu* |
|---|---|---|---|---|---|
| **`openai/gpt-oss-120b`** | **12/12** | **12/12** | — | $0,15 / $0,60 | ok. $0,015 |
| `openai/gpt-oss-20b` | 12/12 | 9/12 | „płyn do naczyń” w kategorii „Inne”; podwójne `add_needs` dla już obecnego mleka; „tak, ale bez kiełbasy” potraktowane jak odmowa (nic nie dodane). Poza asercjami: odpowiedź po angielsku na polską próbę prompt injection | $0,075 / $0,30 | ok. $0,007 |
| `qwen/qwen3.8-27b` (preview) | 8/12 | — | rozumowanie modelu trafia do treści odpowiedzi („I need to call request_finish_shopping…”, „.”); deklaruje zmiany bez wywołania narzędzia (mleko, grill); odpowiedź po polsku na angielską wiadomość | $0,80 / $4,00 | ok. $0,08 |

\* Szacunek: ok. 14 wiadomości i ok. 30 rund modelu na przebieg, jedna runda to ok. 1,4–2 tys.
tokenów wejścia (prompt + narzędzia + lista) i kilkaset tokenów wyjścia (z rozumowaniem). Czas
przebiegu (ok. 9 min) wynika głównie z `EVAL_DELAY_SECONDS`; sama runda z wywołaniem narzędzia
trwała ok. 1,9 s (120b) i 1,1 s (20b).

**Wybrany model: `openai/gpt-oss-120b` na Groq.** Jako jedyny przeszedł wszystkie scenariusze
w obu przebiegach. `gpt-oss-20b` jest o połowę tańszy, ale robi realne błędy (zła kategoria,
zduplikowane zapotrzebowanie, źle zrozumiane potwierdzenie z wyjątkiem). Przy cenie rzędu 0,1 grosza
za wiadomość ta oszczędność nie uzasadnia gorszej jakości. Qwen nie nadaje się do produkcji (model
preview, wycieka rozumowanie, pomija narzędzia). Błędy obu tańszych modeli to błędy modelu, nie
promptu (ten sam prompt na 120b przechodzi w całości), więc prompt został bez zmian. Domyślne
`OPENAI_MODEL=gpt-4.1-mini` w `config.py` dotyczy OpenAI (puste `OPENAI_BASE_URL`) i nie było
ewaluowane w tej rundzie (brak klucza OpenAI). Dla Groq ustaw `OPENAI_MODEL=openai/gpt-oss-120b`.

### Wcześniejsze przebiegi (2026-10-21, Groq `openai/gpt-oss-120b`, `EVAL_DELAY_SECONDS=45`, 11 testów)

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

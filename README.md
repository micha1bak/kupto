# Kupto

Czatowa aplikacja do wspólnych list zakupów. Domownicy piszą swobodnym językiem, czego
potrzebują („skończyło się mleko”, „coś na grilla w sobotę”), a asystent oparty na LLM (OpenAI lub zgodny dostawca, np. Groq)
zamienia to na wspólną listę gospodarstwa: scala powtórzenia, sumuje ilości, nadaje kategorie
i pamięta, kto czego potrzebuje. Listę można też obsługiwać ręcznie.

## Architektura

```
przeglądarka ──► web (nginx: SPA + proxy /api, bez buforowania dla SSE)
                   │
                   ▼
                 backend (FastAPI) ──► OpenAI Responses API (narzędzia / function calling)
                   │
                   ▼
                 db (PostgreSQL 18)
```

- `backend/` — Python 3.12, FastAPI, SQLAlchemy 2 + Alembic; szczegóły w `backend/README.md`.
- `frontend/` — React + Vite + TypeScript; szczegóły w `frontend/README.md`.
- `openspec/` — specyfikacje i plan zmian (OpenSpec).

Model nigdy nie zmienia bazy bezpośrednio: wybiera narzędzie (np. „dodaj zapotrzebowanie”),
a backend wykonuje je w kontekście gospodarstwa zalogowanego użytkownika, z tymi samymi regułami
co ręczne operacje w UI.

## Uruchomienie lokalne (Docker)

```bash
cp .env.example .env
# uzupełnij DB_PASSWORD, JWT_SECRET (np. `openssl rand -hex 32`) i OPENAI_API_KEY;
# lokalnie przez http://localhost ustaw COOKIE_SECURE=false
docker compose up -d --build
```

Aplikacja: <http://localhost:3000>. Backend przy starcie sam wykonuje migracje bazy.
Do pracy nad kodem z przeładowaniem na żywo uruchom backend i frontend osobno (patrz README
w ich katalogach).

## Zmienne środowiskowe

Opisane w `.env.example`:

| Zmienna | Opis |
|---|---|
| `DB_USER`, `DB_PASSWORD`, `DB_NAME` | dane bazy w kontenerze `db` |
| `JWT_SECRET` | sekret podpisu sesji |
| `COOKIE_SECURE` | `true` przy HTTPS (zalecane); `false` tylko przy czystym HTTP |
| `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL` | dostęp do modelu (puste `OPENAI_BASE_URL` = OpenAI) |
| `CHAT_RATE_LIMIT_PER_HOUR` | limit wiadomości do asystenta na użytkownika |

## CI

Workflow `.github/workflows/ci.yml` (GitHub Actions) uruchamia się na każdym pull requeście
i po pushu do `main`; nowy push do tego samego PR anuluje poprzedni przebieg. Joby:

- **Backend** — `uv sync --locked`, `ruff check`, `ruff format --check`, `pytest` (Postgres
  w testcontainers; ewaluacje z prawdziwym modelem są pomijane, klucz API nie jest potrzebny);
- **Frontend** — `npm ci`, sprawdzenie typów (`tsc -b`), Vitest, `vite build`;
- **Docker (backend)**, **Docker (frontend)** — budowa obu obrazów bez publikowania.

CI niczego nie wdraża ani nie publikuje.

## Wdrożenie

Automatyczne wdrażanie na VPS (GitHub Actions) zostało usunięte — docelową produkcją będzie AWS,
a konfiguracja wdrożenia jest jeszcze do przygotowania. Merge do `main` niczego nie wdraża.

Co trzeba zapewnić w docelowym środowisku:

- obrazy `backend/` i `frontend/` (Dockerfile w katalogach) oraz PostgreSQL 18;
- zmienne środowiskowe z `.env.example` dla backendu; `JWT_SECRET` (min. 32 znaki) jest
  wymagany — bez niego backend nie wystartuje;
- HTTPS przed aplikacją i `COOKIE_SECURE=true`;
- backend przy starcie sam wykonuje migracje (`alembic upgrade head`);
- `frontend/nginx.conf` przekazuje `/api` do hosta `backend:8000` przez resolver DNS Dockera
  (`127.0.0.11`) — poza Docker Compose (np. ECS, load balancer) adres backendu i resolver trzeba
  dostosować.

**Dane starej aplikacji (TypeScript)** zostają na VPS w wolumenie `db_prod` i nie są migrowane
do nowego schematu. Jeśli są potrzebne, zrób kopię przed wyłączeniem VPS:
`docker compose exec db pg_dump -U "$DB_USER" "$DB_NAME" > kupto-v1-$(date +%F).sql`.

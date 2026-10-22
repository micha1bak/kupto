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

Lista jest na żywo: każda zmiana (ręczna lub przez czat) wysyła w transakcji Postgres `NOTIFY`,
backend nasłuchuje `LISTEN` i przekazuje otwartym klientom gospodarstwa sygnał przez SSE
(`/api/list/events`), a klient pobiera wtedy listę od nowa.

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
| `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT` | powiadomienia push (opcjonalne; puste = wyłączone), zob. `deploy/README.md` |

## CI

Workflow `.github/workflows/ci.yml` (GitHub Actions) uruchamia się na każdym pull requeście
i po pushu do `main`; nowy push do tego samego PR anuluje poprzedni przebieg. Joby:

- **Backend** — `uv sync --locked`, `ruff check`, `ruff format --check`, `pytest` (Postgres
  w testcontainers; ewaluacje z prawdziwym modelem są pomijane, klucz API nie jest potrzebny);
- **Frontend** — `npm ci`, sprawdzenie typów (`tsc -b`), Vitest, `vite build`;
- **Docker (backend)**, **Docker (frontend)** — budowa obu obrazów bez publikowania.

Sam `ci.yml` niczego nie wdraża ani nie publikuje — publikację obrazów opisuje sekcja „Wdrożenie”.

## Wdrożenie

Produkcja działa na AWS wg [ADR 0001](docs/adr/0001-architektura-aws.md): jedna instancja EC2
(arm64) w projekcie `kupto` (`eu-north-1`) z Docker Compose.

- `infra/` — infrastruktura w Terraformie (instancja, adres IP, rola, bucket kopii);
  szczegóły w [`infra/README.md`](infra/README.md).
- `deploy/` — wdrożenie: po merge do `main` workflow **Publikacja obrazów** publikuje obrazy
  `linux/arm64` w GHCR, a serwer co 5 minut sam je pobiera i odtwarza zmienione kontenery;
  sekrety w SSM Parameter Store. Szczegóły w [`deploy/README.md`](deploy/README.md).

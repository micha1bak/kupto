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

## Wdrożenie

Push do `main` uruchamia `.github/workflows/deploy.yml`: SSH na VPS → `git pull` →
`docker compose up -d --build` w `/root/kupto`.

**Pierwsze wdrożenie wersji 2 (Python)** — schemat bazy jest nowy, dane starej aplikacji nie są
migrowane:

1. Na VPS zrób kopię starej bazy, póki działa stary kontener:
   `docker compose exec db pg_dump -U "$DB_USER" "$DB_NAME" > ~/kupto-v1-$(date +%F).sql`
2. Uzupełnij `/root/kupto/.env` o nowe zmienne z `.env.example` (`OPENAI_API_KEY`,
   `OPENAI_MODEL`, `COOKIE_SECURE`, `CHAT_RATE_LIMIT_PER_HOUR`). `DB_HOST` i `DB_PORT` nie są
   już potrzebne.
3. Zmerguj zmiany do `main`. Nowa baza powstaje na wolumenie `db_v2`; stary wolumen `db_prod`
   zostaje nietknięty.
4. Smoke test: rejestracja, utworzenie gospodarstwa, wiadomość w czacie, odhaczenie pozycji.

**Rollback:** `git revert` merge'a (albo checkout poprzedniego commita na VPS) i
`docker compose up -d --build` — poprzednia konfiguracja używa wolumenu `db_prod` ze starymi
danymi. Stary wolumen usuń ręcznie (`docker volume rm kupto_db_prod`) dopiero po okresie
stabilizacji.

Baza nie jest już wystawiona publicznie (port 5432 tylko na `127.0.0.1`). Dostęp z komputera
deweloperskiego: `ssh -N -L 5432:127.0.0.1:5432 <vps>`.

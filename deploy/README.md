# Wdrożenie produkcyjne

Serwer z `infra/` sam pobiera nowe wersje (ADR 0001): GitHub Actions nie ma dostępu do AWS,
bo zasady projektu blokują OIDC.

1. Merge do `main` → workflow **Publikacja obrazów** (`.github/workflows/publish.yml`) buduje
   obrazy `linux/arm64` na runnerze arm64 i publikuje je w GHCR:
   `ghcr.io/micha1bak/kupto-backend` i `ghcr.io/micha1bak/kupto-frontend`, tagi `main`
   i `sha-<commit>`. Pakiety muszą być publiczne — serwer pobiera je bez logowania.
2. Na serwerze `kupto-update.timer` co 5 minut uruchamia `kupto-update.sh`:
   - `git reset --hard origin/main` w `/opt/kupto/repo` (konfiguracja z `deploy/`),
   - aktualizacja jednostek systemd, jeśli zmieniły się w repo,
   - `/opt/kupto/.env` z parametrów SSM `/kupto/*`,
   - `docker compose pull` i `up -d --wait` — odtwarzane są tylko kontenery z nowym obrazem
     lub konfiguracją; migracje bazy wykonuje backend przy starcie,
   - sprawdzenie `http://localhost/api/health`.

Od merge do działającej wersji mija zwykle 5–10 minut (budowa obrazów + najbliższy tick
timera).

## Sekrety (SSM Parameter Store)

Wszystkie jako `SecureString` w regionie `eu-north-1`, nazwy = zmienne środowiskowe z
`.env.example`:

| Parametr | Wartość |
|---|---|
| `/kupto/DB_USER`, `/kupto/DB_NAME` | `kupto` |
| `/kupto/DB_PASSWORD` | losowe, tylko `[a-f0-9]` (trafia do `DATABASE_URL`) |
| `/kupto/JWT_SECRET` | losowe, ≥ 32 znaki |
| `/kupto/COOKIE_SECURE` | `true` |
| `/kupto/OPENAI_API_KEY` | osobny klucz Groq dla produkcji |
| `/kupto/OPENAI_BASE_URL` | `https://api.groq.com/openai/v1` |
| `/kupto/OPENAI_MODEL` | `openai/gpt-oss-120b` |
| `/kupto/CHAT_RATE_LIMIT_PER_HOUR` | `30` |

Klucz wpisuje się bez pokazywania go na ekranie i bez zapisu w historii powłoki:

```bash
read -rsp 'Klucz Groq: ' KEY && echo && aws ssm put-parameter --profile kupto --name /kupto/OPENAI_API_KEY --type SecureString --overwrite --value "$KEY"; unset KEY
```

Zmiana sekretu działa przy najbliższym ticku timera (odtwarzany jest kontener, którego
zmienne się zmieniły).

## Instalacja na nowym serwerze

Jednorazowo, przez SSM (bez SSH):

```bash
aws ssm send-command --profile kupto --instance-ids "$(terraform -chdir=infra output -raw instance_id)" \
  --document-name AWS-RunShellScript \
  --parameters 'commands=["dnf install -y git","test -d /opt/kupto/repo/.git || git clone https://github.com/micha1bak/kupto.git /opt/kupto/repo","/opt/kupto/repo/deploy/install.sh"]'
```

## Diagnostyka

Powłoka na serwerze: `aws ssm start-session --profile kupto --target <instance_id>`.

- `systemctl list-timers kupto-update.timer` — kiedy następne sprawdzenie,
- `journalctl -u kupto-update -n 50` — wynik ostatnich wdrożeń,
- `docker compose -p kupto ps` / `docker compose -p kupto logs backend` — stan aplikacji.

Do czasu HTTPS (#19) aplikacja odpowiada tylko po HTTP na porcie 80, a przy
`COOKIE_SECURE=true` logowanie w przeglądarce nie działa — to zamierzone.

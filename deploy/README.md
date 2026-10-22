# Wdrożenie produkcyjne

Serwer z `infra/` sam pobiera nowe wersje (ADR 0001): GitHub Actions nie ma dostępu do AWS,
bo zasady projektu blokują OIDC.

1. Merge do `main` → workflow **Publikacja obrazów** (`.github/workflows/publish.yml`) buduje
   obrazy `linux/arm64` na runnerze arm64 i publikuje je w GHCR:
   `ghcr.io/micha1bak/kupto-backend` i `ghcr.io/micha1bak/kupto-frontend`, tagi `main`
   i `sha-<commit>`. Pakiety muszą być publiczne — serwer pobiera je bez logowania.
2. Na serwerze `kupto-update.timer` co 5 minut uruchamia `kupto-update.sh`:
   - `git reset --hard origin/main` w `/opt/kupto/repo` (konfiguracja z `deploy/`),
   - aktualizacja jednostek systemd, jeśli zmieniły się w repo, i włączenie timerów z tablicy
     `timers` (nowy timer działa najpóźniej po dwóch tickach od merge — pierwszy tick wykonuje
     jeszcze starą wersję skryptu),
   - `/opt/kupto/.env` z parametrów SSM `/kupto/*`,
   - `docker compose pull` i `up -d --wait` — odtwarzane są tylko kontenery z nowym obrazem
     lub konfiguracją; migracje bazy wykonuje backend przy starcie,
   - sprawdzenie `/api/health` wewnątrz sieci Compose (`web` → `backend`).

Na zewnątrz wystawiony jest tylko Caddy (porty 80 i 443): certyfikat Let's Encrypt dla
`KUPTO_DOMAIN`, przekierowanie HTTP → HTTPS i proxy do `web` (nginx: SPA + `/api`).
Certyfikaty leżą w wolumenie `caddy_data`.

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
| `/kupto/KUPTO_DOMAIN` | `kupto.bakweb.pl` — rekord A na Elastic IP z `infra/` (DNS w SEOHOST) |

Wyjątek: `/kupto/BACKUP_BUCKET` (`String`, nazwa bucketu na zrzuty bazy) tworzy Terraform
(`infra/storage.tf`) — nie ustawia się go ręcznie.

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

## Kopie zapasowe (#22)

- **Codzienny zrzut bazy:** `kupto-backup.timer` około 03:00 UTC (losowo do 30 min później;
  zaległy zrzut wykona się po starcie serwera) uruchamia `kupto-backup.sh`: `pg_dump -Fc`
  z kontenera `db` do pliku tymczasowego, sprawdzenie przez `pg_restore --list` i wysyłka do
  `s3://<BACKUP_BUCKET>/postgres/<RRRR-MM-DDTHHMMSSZ>.dump`. Zrzuty wygasają po 35 dniach
  (lifecycle bucketu). Zrzut i wdrożenie dzielą blokadę `/run/kupto.lock`, więc
  `kupto-update` nie odtworzy kontenera `db` w trakcie zrzutu.
- **Cotygodniowa kopia dysku:** AWS Backup (`infra/backup.tf`, plan `kupto-weekly`, sejf
  `kupto`) w niedzielę o 02:00 UTC robi snapshot wolumenów z tagiem `Backup = weekly`
  (dysk systemowy serwera) i trzyma go 28 dni.

Sprawdzenie: `systemctl list-timers kupto-backup.timer`, `journalctl -u kupto-backup -n 20`,
lokalnie `aws s3 ls --profile kupto "s3://$(terraform -chdir=infra output -raw backup_bucket)/postgres/"`
i `aws backup list-recovery-points-by-backup-vault --profile kupto --backup-vault-name kupto`.
Zrzut na żądanie: `systemctl start kupto-backup`.

### Odtworzenie bazy ze zrzutu

Na serwerze (`aws ssm start-session ...`, potem `sudo -i`). Zastępuje całą bazę stanem ze
zrzutu; procedurę (dump tym samym poleceniem co skrypt, `dropdb`/`createdb`, `pg_restore`,
migracje po odtworzeniu) przetestowano lokalnie na Postgres 18.1 w #22.

```bash
export AWS_DEFAULT_REGION=eu-north-1
# Bez wdrożeń w trakcie (kupto-update uruchomiłby zatrzymany backend).
systemctl stop kupto-update.timer kupto-backup.timer
cd /opt/kupto/repo/deploy
c() { flock /run/kupto.lock docker compose --env-file /opt/kupto/.env "$@"; }

bucket=$(aws ssm get-parameter --name /kupto/BACKUP_BUCKET --query Parameter.Value --output text)
aws s3 ls "s3://$bucket/postgres/" | tail -5
aws s3 cp "s3://$bucket/postgres/<plik>.dump" /var/tmp/kupto.dump

c stop backend
c exec -T db sh -c 'dropdb -U "$POSTGRES_USER" --force "$POSTGRES_DB" && createdb -U "$POSTGRES_USER" "$POSTGRES_DB"'
c exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --exit-on-error --single-transaction' </var/tmp/kupto.dump
c start backend   # przy starcie wykona migracje, jeśli zrzut jest starszy niż kod

systemctl start kupto-update.timer kupto-backup.timer
rm /var/tmp/kupto.dump
```

Zrzut można też odtworzyć lokalnie: pobrać go `aws s3 cp --profile kupto ...` i wykonać ten
sam `pg_restore` w kontenerze `db` z `docker-compose.yml` w katalogu głównym.

### Odtworzenie dysku z AWS Backup

Gdy zepsuty jest cały serwer (system, `.env`, certyfikaty), a nie tylko dane. Kopia jest
spójna jak po nagłym wyłączeniu — Postgres odtworzy się z WAL przy starcie; dane od kopii
do awarii można potem nadpisać nowszym zrzutem z S3 (wyżej).

```bash
# Najnowszy punkt przywracania; ARN ma postać arn:aws:ec2:eu-north-1::snapshot/snap-...
aws backup list-recovery-points-by-backup-vault --profile kupto --backup-vault-name kupto \
  --query 'reverse(sort_by(RecoveryPoints,&CreationDate))[].[CreationDate,Status,RecoveryPointArn]' --output table

# Podmiana dysku systemowego na snapshot (instancja, Elastic IP i rola zostają; serwer się
# restartuje, stary wolumen zostaje do ręcznego usunięcia).
aws ec2 create-replace-root-volume-task --profile kupto \
  --instance-id "$(terraform -chdir=infra output -raw instance_id)" --snapshot-id snap-...
aws ec2 describe-replace-root-volume-tasks --profile kupto
```

Nowy wolumen może nie mieć tagu `Backup = weekly` — po podmianie `terraform plan` pokaże
różnicę w `root_block_device`, a `terraform apply` przywróci tag (zmiana w miejscu).
Alternatywa: AWS Backup → Protected resources → Restore tworzy osobny wolumen ze snapshotu
(rola `kupto-backup`), który można podpiąć ręcznie.

## Diagnostyka

Powłoka na serwerze: `aws ssm start-session --profile kupto --target <instance_id>`.

- `systemctl list-timers kupto-update.timer` — kiedy następne sprawdzenie,
- `journalctl -u kupto-update -n 50` — wynik ostatnich wdrożeń,
- `systemctl list-timers 'kupto-*'`, `journalctl -u kupto-backup -n 20` — zrzuty bazy,
- `docker compose -p kupto ps` / `docker compose -p kupto logs backend` — stan aplikacji,
- `docker compose -p kupto logs caddy` — wydawanie i odnawianie certyfikatu.

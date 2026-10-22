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
| `/kupto/VAPID_PUBLIC_KEY`, `/kupto/VAPID_PRIVATE_KEY` | para kluczy Web Push z `uv run python -m kupto.push.keys` (niżej); opcjonalne — bez nich powiadomienia są wyłączone |
| `/kupto/VAPID_SUBJECT` | `https://kupto.bakweb.pl` (kontakt dla usług push; może być też `mailto:…`) |

Wyjątek: `/kupto/BACKUP_BUCKET` (`String`, nazwa bucketu na zrzuty bazy) tworzy Terraform
(`infra/storage.tf`) — nie ustawia się go ręcznie.

Klucz wpisuje się bez pokazywania go na ekranie i bez zapisu w historii powłoki:

```bash
read -rsp 'Klucz Groq: ' KEY && echo && aws ssm put-parameter --profile kupto --name /kupto/OPENAI_API_KEY --type SecureString --overwrite --value "$KEY"; unset KEY
```

Zmiana sekretu działa przy najbliższym ticku timera (odtwarzany jest kontener, którego
zmienne się zmieniły).

### Klucze powiadomień push (VAPID, #27)

Jednorazowo, z katalogu `backend/` (klucze trafiają do zmiennych powłoki, nie na ekran ani do
historii). Bez `--overwrite`: nowa para kluczy unieważnia subskrypcje wszystkich urządzeń, więc
istniejących parametrów nie nadpisujemy przypadkiem.

```bash
cd backend && eval "$(uv run python -m kupto.push.keys)" \
  && aws ssm put-parameter --profile kupto --name /kupto/VAPID_PUBLIC_KEY --type SecureString --value "$VAPID_PUBLIC_KEY" \
  && aws ssm put-parameter --profile kupto --name /kupto/VAPID_PRIVATE_KEY --type SecureString --value "$VAPID_PRIVATE_KEY" \
  && aws ssm put-parameter --profile kupto --cli-input-json '{"Name": "/kupto/VAPID_SUBJECT", "Type": "SecureString", "Value": "https://kupto.bakweb.pl"}'
unset VAPID_PUBLIC_KEY VAPID_PRIVATE_KEY
```

(`--cli-input-json` dla adresu URL: AWS CLI v1 traktuje wartość `https://…` z `--value` jako
adres do pobrania.) Po najbliższym ticku `docker compose -p kupto logs backend` nie powinien
zawierać „Powiadomienia push wyłączone”, a w aplikacji (strona gospodarstwa) pojawi się
przycisk „Włącz powiadomienia”. Błędne lub niepasujące klucze nie zatrzymują backendu — tylko
wyłączają powiadomienia z błędem w logu.

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

## Przypomnienia o zwykłych produktach (#40)

`kupto-reminders.timer` codziennie o **17:00 czasu polskiego** (`OnCalendar` ze strefą
`Europe/Warsaw`, więc zmiana czasu nie przesuwa godziny) uruchamia `kupto-reminders.sh`:
`docker compose exec -T backend python -m kupto.history.reminders` pod blokadą
`/run/kupto.lock` (wdrożenie nie odtworzy backendu w trakcie wysyłki). Komenda przechodzi po
gospodarstwach i wysyła push „Zwykle o tej porze kupujecie” członkom, którzy włączyli typ
„Zwykłe produkty” (domyślnie wyłączony) i mają urządzenie z powiadomieniami.

Limity pilnuje kod, więc ręczne lub nadrobione uruchomienie niczego nie dubluje: najwyżej
jedno przypomnienie na gospodarstwo na dobę czasu polskiego, wysyłka tylko między 9:00 a 21:00
czasu polskiego (`Persistent=true` nadrabia pominięte uruchomienie po starcie serwera, ale nie
w nocy) i tylko gdy jest produkt, o którym gospodarstwo nie dostało przypomnienia od jego
ostatniego zakupu (tabela `usual_reminders`). Bez kluczy VAPID komenda nic nie robi.

Timer instaluje i włącza `kupto-update.sh` (tablice `units` i `timers`) — po merge działa
najpóźniej po dwóch tickach, bez ręcznych kroków.

Sprawdzenie i ręczne uruchomienie (jako root):

```bash
systemctl list-timers kupto-reminders.timer   # następne uruchomienie: 17:00 CET/CEST
systemctl start kupto-reminders               # od razu (w oknie 9–21, limity jak zwykle)
journalctl -u kupto-reminders -n 20           # „Przypomnienia o zwykłych produktach: N z M gospodarstw.”
```

Wyłączenie: `systemctl disable --now kupto-reminders.timer` działa tylko do najbliższego ticku
`kupto-update` (włącza timery z tablicy `timers`) — na stałe trzeba usunąć timer z `timers`
w repo. Użytkownik wyłącza przypomnienia sam, przełącznikiem na stronie gospodarstwa.

## Diagnostyka

Powłoka na serwerze: `aws ssm start-session --profile kupto --target <instance_id>`.

- `systemctl list-timers kupto-update.timer` — kiedy następne sprawdzenie,
- `journalctl -u kupto-update -n 50` — wynik ostatnich wdrożeń,
- `systemctl list-timers 'kupto-*'`, `journalctl -u kupto-backup -n 20` — zrzuty bazy,
- `journalctl -u kupto-reminders -n 20` — przypomnienia o zwykłych produktach,
- `docker compose -p kupto ps` / `docker compose -p kupto logs backend` — stan aplikacji,
- `docker compose -p kupto logs caddy` — wydawanie i odnawianie certyfikatu.

## Logi i koszty (#23)

### Logi backendu

Backend pisze na stdout jeden obiekt JSON na linię (`ts`, `level`, `logger`, `message`
i pola zdarzenia, np. `event`, `user_id`, `household_id`; błędy z `exc_info`). Trafiają tam
loggery `kupto.*` i uvicorn (`event: http_request` z metodą, ścieżką i kodem odpowiedzi). Do
logów nie trafiają treści wiadomości czatu, hasła, ciasteczka ani klucze.

Kontener `backend` loguje do journald (tag `kupto-backend`), a nie do plików json-file jak
pozostałe — logi przeżywają odtworzenie kontenera przy wdrożeniu. Czytanie:

```bash
docker compose -p kupto logs --since 1h backend               # jak dotąd
journalctl -t kupto-backend --since today -o cat | grep '"level": "ERROR"'
```

Retencję wyznacza journald (domyślnie do 10% dysku); `journalctl --disk-usage`,
w razie potrzeby `journalctl --vacuum-time=60d`.

Poziom logów: opcjonalny parametr SSM `/kupto/LOG_LEVEL` (`DEBUG`, `INFO` — domyślnie,
`WARNING`, `ERROR`; wielkimi literami), działa od najbliższego ticku timera.

### Zużycie tokenów LLM

Po każdej turze czatu backend loguje zdarzenie `llm_usage` — bez treści rozmowy:

```json
{"ts": "2026-10-22T12:24:18.302+00:00", "level": "INFO", "logger": "kupto.chat.router", "message": "Zużycie modelu: 4831 wej. / 72 wyj. tokenów", "event": "llm_usage", "outcome": "ok", "model": "openai/gpt-oss-120b", "user_id": 1, "household_id": 1, "input_tokens": 4831, "output_tokens": 72, "cached_tokens": 1024, "reasoning_tokens": 24, "model_calls": 2, "tool_rounds": 1, "tool_calls": ["add_needs"], "duration_ms": 1282}
```

Tokeny są sumą wszystkich wywołań modelu w turze (`model_calls`; `tool_rounds` — rundy
z narzędziami). `outcome`: `ok`, `llm_unavailable` (błąd dostawcy), `error` (błąd aplikacji),
`cancelled` (klient zamknął strumień). Zero tokenów przy `ok` oznacza, że dostawca nie
zwrócił zużycia.

Podsumowanie dzienne (UTC) i na użytkownika z szacunkowym kosztem — na serwerze jako root:

```bash
/opt/kupto/repo/deploy/kupto-usage.sh                         # ostatnie 7 dni
/opt/kupto/repo/deploy/kupto-usage.sh 2026-10-01 2026-11-01   # --since / --until journalctl
docker compose -p kupto logs --no-log-prefix backend | /opt/kupto/repo/deploy/kupto-usage.sh -
```

```text
Dziennie (UTC)
dzień                  tury  błędy     wejście     z cache     wyjście  koszt USD
2026-10-20                3      0       13331        2048         631     0.0022
2026-10-21                4      1       18379        5120         399     0.0026
razem                     7      1       31710        7168        1030     0.0048
...
```

Koszt liczony wg cennika Groq dla `openai/gpt-oss-120b` (0,15 USD / 1 mln tokenów wejścia,
0,075 z cache, 0,60 wyjścia — październik 2026); inne ceny przez zmienne `PRICE_INPUT`,
`PRICE_CACHED`, `PRICE_OUTPUT`. Rozliczenie u dostawcy jest wiążące — skrypt służy do
wychwycenia, kto i kiedy zużywa najwięcej.

### Limit wydatków u dostawcy LLM (Groq)

Twardy limit ustawia się w konsoli Groq
([dokumentacja](https://console.groq.com/docs/spend-limits)): **Settings → Billing →
Limits** — miesięczny limit w USD i progi powiadomień e-mail (np. 50%, 75%, 90%; adresy
w **Settings → Billing → Manage**). Wymaga planu płatnego (Developer) i roli właściciela
organizacji. Na planie darmowym nie ma ani opłat, ani limitów wydatków — ograniczeniem są
tylko limity zapytań.

- Po osiągnięciu limitu Groq odrzuca nowe zapytania z każdego klucza organizacji (HTTP 400,
  `blocked_api_access`) — czat pokaże „Asystent jest chwilowo niedostępny”, a w logach
  pojawi się `llm_unavailable`. Lista działa dalej.
- Limit odnawia się 1. dnia miesiąca; limitów dziennych i tygodniowych nie ma.
- Zużycie jest liczone z opóźnieniem 10–15 minut, więc limit może zostać lekko przekroczony.
- Dla tej skali wystarczy kilka USD miesięcznie; aplikacja dodatkowo ogranicza liczbę
  wiadomości (`CHAT_RATE_LIMIT_PER_HOUR`).

### Budżet i alarmy AWS

Miesięczny budżet AWS Budgets i alarmy CloudWatch (serwer nie przechodzi kontroli stanu,
płatne kredyty CPU) są w `infra/budgets.tf` — konfiguracja i adres powiadomień:
[infra/README.md](../infra/README.md#budżet-i-alarmy-23).

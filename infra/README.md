# Infrastruktura AWS (Terraform)

Infrastruktura produkcyjna wg [ADR 0001](../docs/adr/0001-architektura-aws.md): jedna instancja
EC2 `t4g.micro` w projekcie `kupto` (`eu-north-1`), Elastic IP, security group tylko na 80/443,
rola instancji (Session Manager, zrzuty bazy w S3, sekrety z SSM), bucket na zrzuty bazy
(z parametrem SSM `/kupto/BACKUP_BUCKET` dla skryptu na serwerze) i cotygodniowe kopie dysku
przez AWS Backup (`backup.tf`), a także budżet kosztów i alarmy e-mail (`budgets.tf`).

## Wymagania

- Terraform ≥ 1.10 (stan w S3 z natywnym blokowaniem `use_lockfile`).
- AWS CLI v2 zalogowane do projektu: `aws login --profile kupto` (sesja projektu `kupto`,
  region `eu-north-1`). Poświadczenia wygasają po 12 h — wtedy zaloguj się ponownie.

## Pierwsze uruchomienie

1. Bucket na stan (jednorazowo, stan lokalny w `bootstrap/`, poza repo):

   ```bash
   cd infra/bootstrap
   terraform init
   terraform apply
   ```

2. Właściwa infrastruktura — bucket stanu podawany przy `init`, żeby numer konta nie trafiał
   do publicznego repo:

   ```bash
   cd infra
   terraform init -backend-config="bucket=kupto-tfstate-$(aws sts get-caller-identity --profile kupto --query Account --output text)"
   export TF_VAR_budget_email='adres@domena'   # powiadomienia budżetu i alarmów (niżej)
   terraform plan
   terraform apply
   ```

`terraform output` pokazuje m.in. stały adres IP (rekord A subdomeny, #19) i polecenie do
otwarcia powłoki na serwerze przez Session Manager (bez SSH; wymaga `session-manager-plugin`).

## Ważne

- Ograniczenia projektu (SCP): zasoby regionalne tylko w `eu-north-1`; w IAM nie da się
  utworzyć dostawcy OIDC, dlatego GitHub Actions nie loguje się do AWS — serwer sam pobiera
  nowe obrazy z GHCR (ADR 0001, #21).
- Dysk systemowy ma `delete_on_termination = false`, a zmiany AMI i `user_data` są
  ignorowane, żeby `apply` nigdy nie podmienił serwera z danymi bazy. Po świadomym usunięciu
  instancji stary wolumen trzeba usunąć ręcznie.
- `user_data` przygotowuje tylko Dockera, Compose i swap; aplikację wdrażają #19–#21.
- Kopie (#22): AWS Backup wybiera wolumeny po tagu `Backup = weekly` (ustawionym na dysku
  systemowym w `main.tf`; zmiana tagu nie wymienia instancji). Rola `kupto-backup` ma
  zarządzane polityki AWS Backup do kopii i odtwarzania. Sejf `kupto` nie usunie się przez
  `terraform destroy`, dopóki są w nim punkty przywracania. Rola instancji może zapisywać
  i czytać `postgres/*` w buckecie, ale nie usuwać — zrzuty wygasają przez lifecycle.
  Procedury odtworzenia: [deploy/README.md](../deploy/README.md#kopie-zapasowe-22).

## Budżet i alarmy (#23)

`budgets.tf`:

- **AWS Budgets** `kupto-miesiecznie` — miesięczny budżet kosztów (`monthly_budget_usd`,
  domyślnie 15 USD) z e-mailem przy prognozie > 80% i faktycznych kosztach > 100%. Liczy koszt
  przed odjęciem kredytów (`include_credit = false`), więc ostrzega o tempie zużywania
  kredytów planu Free, a nie dopiero po ich wyczerpaniu. Dane kosztowe AWS aktualizuje kilka
  razy na dobę, więc powiadomienie przychodzi z opóźnieniem.
- **Alarmy CloudWatch → SNS `kupto-alerts` → e-mail:**
  `kupto-status-check-failed` (instancja nie przechodzi kontroli stanu EC2 przez 5 minut lub
  nie raportuje metryki; wiadomość także po powrocie do normy) i `kupto-cpu-surplus-charged`
  (t4g w trybie `unlimited` nalicza płatne kredyty CPU). Metryki EC2 i te dwa alarmy mieszczą
  się w darmowym limicie CloudWatch (10 alarmów).

Adres powiadomień to zmienna `budget_email` **bez wartości domyślnej** — nie wpisuj go do
repo ani do `*.tfvars` w repo. Podawaj przy każdym `plan`/`apply`:

```bash
export TF_VAR_budget_email='adres@domena'   # albo: terraform apply -var budget_email=adres@domena
```

Po pierwszym `apply` AWS SNS wysyła e-mail „AWS Notification - Subscription Confirmation” —
alarmy zaczną przychodzić dopiero po kliknięciu linku. Budżet wysyła e-maile bez
potwierdzenia. Sprawdzenie: `aws budgets describe-budgets --profile kupto --account-id
"$(aws sts get-caller-identity --profile kupto --query Account --output text)"`,
`aws cloudwatch describe-alarms --profile kupto --alarm-name-prefix kupto-`,
`aws sns list-subscriptions-by-topic --profile kupto --topic-arn <arn kupto-alerts>`.

## Wysyłka maili — Amazon SES (#77)

`ses.tf`: tożsamość domenowa SES `kupto.bakweb.pl` (zmienna `mail_domain`) z Easy DKIM
(RSA 2048) i własną domeną MAIL FROM `mail.kupto.bakweb.pl`; `iam.tf`: rola instancji może
wywołać `ses:SendEmail` tylko dla tej tożsamości i tylko z adresów `*@kupto.bakweb.pl`;
`main.tf`: `http_put_response_hop_limit = 2`, żeby kontener backendu (most Dockera to
dodatkowy skok) dostał poświadczenia roli z IMDSv2. Aplikacja wysyła przez API SES v2
(boto3) — bez użytkownika IAM i haseł SMTP.

Do czasu wykonania poniższych kroków produkcja działa z `MAIL_BACKEND=log`: maile nie są
wysyłane, weryfikacja adresów nie jest wymagana, a „Zapomniałem hasła” pokazuje komunikat o
niedostępnej wysyłce. Kroki właściciela, po kolei:

1. **Apply** (z katalogu `infra/`, po `aws login --profile kupto`):

   ```bash
   export TF_VAR_budget_email='adres@domena'
   terraform plan    # oczekiwane: 2 zasoby SES do utworzenia, zmiana w miejscu polityki
                     # kupto-app i metadata_options instancji (bez jej wymiany)
   terraform apply
   terraform output ses_dns_records
   ```

2. **Rekordy DNS w SEOHOST** (strefa `bakweb.pl`) — dokładnie te z `ses_dns_records`:
   - 3 × `CNAME` `<token>._domainkey.kupto.bakweb.pl` → `<token>.dkim.amazonses.com` (DKIM),
   - `MX` `mail.kupto.bakweb.pl` → `10 feedback-smtp.eu-north-1.amazonses.com` (MAIL FROM),
   - `TXT` `mail.kupto.bakweb.pl` → `v=spf1 include:amazonses.com ~all` (SPF dla MAIL FROM),
   - `TXT` `_dmarc.kupto.bakweb.pl` → `v=DMARC1; p=none` (DMARC; po kilku tygodniach bez
     problemów można zaostrzyć do `p=quarantine`; adres raportów `rua=mailto:…` opcjonalnie).

   Jeśli panel SEOHOST dopisuje domenę strefy sam, wpisz nazwy bez `.bakweb.pl`
   (np. `abc123._domainkey.kupto`). Weryfikacja trwa zwykle od kilku minut do kilku godzin:

   ```bash
   $(terraform output -raw ses_identity_status)   # verified: true, dkim: SUCCESS, mail_from: SUCCESS
   ```

3. **Wyjście z sandboxa SES.** Nowe konto SES może wysyłać tylko na zweryfikowane adresy
   (do 200 maili na dobę). Wniosek o production access — konsola SES (eu-north-1) → *Account
   dashboard* → *Request production access*, albo:

   ```bash
   aws sesv2 put-account-details --profile kupto --region eu-north-1 \
     --production-access-enabled --mail-type TRANSACTIONAL \
     --website-url https://kupto.bakweb.pl --contact-language EN \
     --use-case-description "Transactional e-mails of a small household shopping-list app: address verification links and password reset links, sent only on user action. Expected volume: under 50 e-mails per day. Bounces and complaints are monitored in the SES console."
   aws sesv2 get-account --profile kupto --region eu-north-1 --query '{prod: ProductionAccessEnabled, review: Details.ReviewDetails.Status}'
   ```

   Odpowiedź AWS przychodzi zwykle w ciągu doby. Do tego czasu można sprawdzić wysyłkę na
   własny, zweryfikowany adres (`aws sesv2 create-email-identity --email-identity adres@domena`
   i kliknięcie linku z maila od AWS).

4. **Parametry SSM** — włączenie wysyłki w aplikacji (działa od najbliższego ticku
   `kupto-update`, zob. [deploy/README.md](../deploy/README.md#sekrety-ssm-parameter-store)):

   ```bash
   aws ssm put-parameter --profile kupto --name /kupto/MAIL_FROM --type SecureString \
     --value 'Kupto <no-reply@kupto.bakweb.pl>'
   aws ssm put-parameter --profile kupto --name /kupto/MAIL_BACKEND --type SecureString --value ses
   ```

   `KUPTO_DOMAIN` (już ustawiony) wyznacza adres w linkach (`https://kupto.bakweb.pl/...`).
   Region SES to domyślnie `eu-north-1` (`MAIL_SES_REGION`). Sprawdzenie po wdrożeniu:
   `docker compose -p kupto logs backend | grep -i mail` powinno pokazać „Wysyłka maili przez
   Amazon SES”; po rejestracji testowego konta — zdarzenie `mail_sent` (bez adresu i treści).
   Błąd wysyłki daje zdarzenie `mail_failed` z typem wyjątku (np. `MessageRejected` w
   sandboxie, `NoCredentialsError` przy hop limicie 1).

Wycofanie: `aws ssm delete-parameter --profile kupto --name /kupto/MAIL_BACKEND` — aplikacja
wraca do `log` (nikt nie jest blokowany do potwierdzenia adresu).

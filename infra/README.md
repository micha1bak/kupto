# Infrastruktura AWS (Terraform)

Infrastruktura produkcyjna wg [ADR 0001](../docs/adr/0001-architektura-aws.md): jedna instancja
EC2 `t4g.micro` w projekcie `kupto` (`eu-north-1`), Elastic IP, security group tylko na 80/443,
rola instancji (Session Manager, zrzuty bazy do S3, sekrety z SSM) i bucket na kopie bazy.

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

#!/bin/bash
# Codzienny zrzut bazy do S3, uruchamiany przez kupto-backup.timer (#22). Zrzut trafia najpierw
# do pliku i jest sprawdzany przez `pg_restore --list` — rola instancji nie może usuwać obiektów,
# więc przerwany zrzut wysłany strumieniowo zostałby w buckecie jako „poprawna” kopia.
# Odtworzenie: deploy/README.md. Wynik: journalctl -u kupto-backup.
set -euo pipefail

repo=/opt/kupto/repo
env_file=/opt/kupto/.env

compose() {
  docker compose --project-directory "$repo/deploy" --env-file "$env_file" \
    -f "$repo/deploy/docker-compose.yml" "$@"
}

main() {
  local bucket key
  # Parametr tworzy Terraform (infra/storage.tf) — nazwa bucketu zawiera numer konta.
  bucket=$(aws ssm get-parameter --name /kupto/BACKUP_BUCKET --query Parameter.Value --output text)
  key="postgres/$(date -u +%Y-%m-%dT%H%M%SZ).dump"

  # Globalna, bo pułapka EXIT działa już po wyjściu z main.
  dump=$(mktemp /var/tmp/kupto-dump.XXXXXX)
  trap 'rm -f "$dump"' EXIT

  # Połączenie przez gniazdo w kontenerze (bez hasła); użytkownik i baza ze zmiennych kontenera.
  # shellcheck disable=SC2016  # zmienne mają się rozwinąć w kontenerze, nie tutaj
  compose exec -T db sh -c 'exec pg_dump -Fc -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >"$dump"
  # shellcheck disable=SC2016
  compose exec -T db sh -c 'exec pg_restore --list' <"$dump" >/dev/null

  aws s3 cp --only-show-errors "$dump" "s3://$bucket/$key"
  echo "Zrzut bazy: s3://$bucket/$key ($(stat -c %s "$dump") B)"
}

main "$@"

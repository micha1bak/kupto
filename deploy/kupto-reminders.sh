#!/bin/bash
# Codzienne przypomnienia push o zwykłych produktach (#40), uruchamiane przez
# kupto-reminders.timer. Komenda działa w kontenerze backendu (ten sam obraz, zmienne i klucze
# VAPID); limity — raz dziennie na gospodarstwo, 9–21 czasu polskiego, tylko nowe produkty —
# pilnuje kod (`kupto.history.reminders`), więc ręczne ponowne uruchomienie jest bezpieczne.
# Wynik: journalctl -u kupto-reminders.
set -euo pipefail

repo=/opt/kupto/repo
env_file=/opt/kupto/.env

compose() {
  docker compose --project-directory "$repo/deploy" --env-file "$env_file" \
    -f "$repo/deploy/docker-compose.yml" "$@"
}

compose exec -T backend python -m kupto.history.reminders

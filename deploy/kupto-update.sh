#!/bin/bash
# Wdrożenie na serwerze, uruchamiane co 5 minut przez kupto-update.timer: aktualizuje
# konfigurację z repo, odświeża sekrety z SSM, pobiera obrazy z GHCR i odtwarza tylko
# zmienione kontenery. Wynik: journalctl -u kupto-update.
set -euo pipefail

repo=/opt/kupto/repo
env_file=/opt/kupto/.env
units=(kupto-update.service kupto-update.timer)

compose() {
  docker compose --project-directory "$repo/deploy" --env-file "$env_file" \
    -f "$repo/deploy/docker-compose.yml" "$@"
}

sync_repo() {
  git -C "$repo" fetch --quiet origin main
  git -C "$repo" reset --quiet --hard origin/main
}

sync_units() {
  local unit changed=0
  for unit in "${units[@]}"; do
    if ! cmp -s "$repo/deploy/systemd/$unit" "/etc/systemd/system/$unit"; then
      install -m 0644 "$repo/deploy/systemd/$unit" "/etc/systemd/system/$unit"
      changed=1
    fi
  done
  if [ "$changed" = 1 ]; then
    systemctl daemon-reload
  fi
}

# Parametry /kupto/NAZWA (SecureString) zamieniane na linie NAZWA=wartość.
render_env() {
  local tmp
  tmp=$(mktemp "$env_file.XXXXXX")
  aws ssm get-parameters-by-path --path /kupto/ --with-decryption \
    --query 'Parameters[].[Name,Value]' --output text |
    while IFS=$'\t' read -r name value; do
      printf '%s=%s\n' "${name##*/}" "$value"
    done >"$tmp"
  if [ ! -s "$tmp" ]; then
    rm -f "$tmp"
    echo "Brak parametrów /kupto/* w SSM — patrz deploy/README.md" >&2
    exit 1
  fi
  chmod 600 "$tmp"
  mv "$tmp" "$env_file"
}

main() {
  sync_repo
  sync_units
  render_env
  compose pull --quiet
  compose up -d --remove-orphans --wait --wait-timeout 180
  curl -fsS --retry 10 --retry-delay 3 --retry-all-errors http://localhost/api/health >/dev/null
  docker image prune -f >/dev/null
  echo "Wdrożono $(git -C "$repo" rev-parse --short HEAD); /api/health OK"
}

# Wywołanie na końcu: bash wczytał już cały plik, więc `git reset` w sync_repo może bezpiecznie
# podmienić ten skrypt w trakcie działania.
main "$@"
exit

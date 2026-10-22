#!/bin/bash
# Jednorazowa instalacja wdrożenia na serwerze (idempotentna). Uruchamiana przez SSM jako root:
#   dnf install -y git && git clone https://github.com/micha1bak/kupto.git /opt/kupto/repo \
#     && /opt/kupto/repo/deploy/install.sh
set -euo pipefail

repo=/opt/kupto/repo

dnf install -y git
if [ ! -d "$repo/.git" ]; then
  git clone --quiet https://github.com/micha1bak/kupto.git "$repo"
fi

install -m 0644 "$repo"/deploy/systemd/kupto-{update,backup}.{service,timer} /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now kupto-update.timer kupto-backup.timer
systemctl start kupto-update.service

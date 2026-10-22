#!/bin/bash
# Podsumowanie zużycia tokenów LLM z logów backendu (zdarzenia `llm_usage`): sumy dzienne
# (UTC) i na użytkownika z szacunkowym kosztem. Uruchamiane ręcznie na serwerze jako root:
#   /opt/kupto/repo/deploy/kupto-usage.sh                         # ostatnie 7 dni
#   /opt/kupto/repo/deploy/kupto-usage.sh 2026-10-01 2026-11-01   # okres (--since/--until)
#   ... | kupto-usage.sh -                                        # logi JSON ze stdin
# Ceny (USD za 1 mln tokenów) można nadpisać zmiennymi PRICE_INPUT, PRICE_CACHED,
# PRICE_OUTPUT — domyślne to cennik Groq dla openai/gpt-oss-120b (październik 2026).
set -euo pipefail

since=${1:--7 days}
until=${2:-now}

read_logs() {
  if [ "$since" = - ]; then
    cat
  else
    # Backend loguje do journald z tagiem kupto-backend (deploy/docker-compose.yml), więc logi
    # przeżywają odtworzenie kontenera przy wdrożeniu.
    journalctl --quiet --output cat --identifier kupto-backend --since "$since" --until "$until"
  fi
}

# Python 3.9 z Amazon Linux 2023 — bez składni nowszych wersji.
read -r -d '' summary <<'PY' || true
import json, os, sys
from collections import defaultdict

price_in, price_cached, price_out = (
    float(os.environ.get(k, d)) / 1e6
    for k, d in (("PRICE_INPUT", "0.15"), ("PRICE_CACHED", "0.075"), ("PRICE_OUTPUT", "0.60"))
)
FIELDS = ("turns", "failed", "input", "cached", "output", "cost")


def empty():
    return dict.fromkeys(FIELDS, 0)


days, users = defaultdict(empty), defaultdict(empty)
for line in sys.stdin:
    try:
        e = json.loads(line)
    except ValueError:
        continue  # linie spoza JSON (np. migracje Alembica przy starcie)
    if not isinstance(e, dict) or e.get("event") != "llm_usage":
        continue
    inp, cached, out = (int(e.get(k) or 0) for k in ("input_tokens", "cached_tokens", "output_tokens"))
    cost = (inp - cached) * price_in + cached * price_cached + out * price_out
    for row in (days[e["ts"][:10]], users["%s/%s" % (e.get("user_id"), e.get("household_id"))]):
        row["turns"] += 1
        row["failed"] += e.get("outcome") not in ("ok", "cancelled")
        row["input"] += inp
        row["cached"] += cached
        row["output"] += out
        row["cost"] += cost

HEADER = "{:<20}{:>7}{:>7}{:>12}{:>12}{:>12}{:>11}"
ROW = "{:<20}{turns:>7}{failed:>7}{input:>12}{cached:>12}{output:>12}{cost:>11.4f}"


def table(title, key_header, rows):
    print(title)
    print(HEADER.format(key_header, "tury", "błędy", "wejście", "z cache", "wyjście", "koszt USD"))
    total = empty()
    for key, row in rows:
        print(ROW.format(key, **row))
        for f in FIELDS:
            total[f] += row[f]
    print(ROW.format("razem", **total))
    print()


if not days:
    print("Brak zdarzeń llm_usage w podanym okresie.")
    sys.exit(0)
table("Dziennie (UTC)", "dzień", sorted(days.items()))
table("Na użytkownika (id użytkownika/gospodarstwa)", "użytkownik", sorted(
    users.items(), key=lambda kv: -kv[1]["cost"]
))
PY

read_logs | python3 -I -c "$summary"

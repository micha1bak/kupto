"""Logi strukturalne: jeden obiekt JSON na linię na stdout (`docker compose logs backend`).

Pola dodatkowe przekazuje się przez `extra=`, np.
`logger.info("...", extra={"event": "llm_usage", "input_tokens": 10})`. Do logów nie trafiają
treści wiadomości czatu, hasła, ciasteczka ani klucze — pilnuje tego wywołujący (formatter
zapisuje tylko to, co dostanie).
"""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

# Atrybuty, które ma każdy LogRecord (i kolorowa kopia komunikatu uvicorna) — reszta pochodzi
# z `extra=`.
_STANDARD_ATTRS = frozenset(
    vars(logging.LogRecord("", 0, "", 0, "", None, None)).keys()
    | {"message", "asctime", "color_message"}
)
# Loggery uvicorna mają własne handlery (tekst); przekierowujemy je do wspólnego handlera.
_UVICORN_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.name == "uvicorn.access" and isinstance(record.args, tuple):
            entry.update(_access_fields(record.args))
        for key, value in vars(record).items():
            if key not in _STANDARD_ATTRS and not key.startswith("_"):
                entry[key] = value
        if record.exc_info:
            entry["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False, default=str)


def _access_fields(args: tuple) -> dict[str, Any]:
    # uvicorn.access: (adres klienta, metoda, ścieżka, wersja HTTP, kod odpowiedzi).
    if len(args) != 5:
        return {}
    client, method, path, _, status = args
    return {
        "event": "http_request",
        "client": client,
        "method": method,
        "path": path,
        "status": status,
    }


class _KuptoHandler(logging.StreamHandler):
    """Handler instalowany przez `configure_logging` (ponowne wywołanie go podmienia)."""


def configure_logging(level: str = "INFO") -> None:
    """Kieruje logi aplikacji i uvicorna na stdout jako JSON.

    Idempotentne i nie usuwa obcych handlerów (np. pytest), więc można wołać przy każdym
    `create_app`.
    """
    root = logging.getLogger()
    for handler in [h for h in root.handlers if isinstance(h, _KuptoHandler)]:
        root.removeHandler(handler)
    handler = _KuptoHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level.upper())
    for name in _UVICORN_LOGGERS:
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True

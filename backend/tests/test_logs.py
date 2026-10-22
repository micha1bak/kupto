import json
import logging
import sys

import pytest

from kupto.logs import JsonFormatter, configure_logging


def record(name="kupto.test", msg="Zużycie %d", args=(5,), **extra):
    rec = logging.LogRecord(name, logging.INFO, __file__, 1, msg, args, None)
    rec.__dict__.update(extra)
    return rec


def test_formatter_writes_one_json_object_with_extra_fields():
    line = JsonFormatter().format(record(event="llm_usage", input_tokens=10))

    entry = json.loads(line)
    assert entry["level"] == "INFO"
    assert entry["logger"] == "kupto.test"
    assert entry["message"] == "Zużycie 5"
    assert entry["event"] == "llm_usage"
    assert entry["input_tokens"] == 10
    assert entry["ts"].endswith("+00:00")
    assert "\n" not in line


def test_formatter_includes_exception():
    try:
        raise ValueError("zepsute")
    except ValueError:
        rec = logging.LogRecord("kupto", logging.ERROR, __file__, 1, "błąd", (), sys.exc_info())

    entry = json.loads(JsonFormatter().format(rec))
    assert "ValueError: zepsute" in entry["exc_info"]


def test_uvicorn_access_log_gets_request_fields():
    rec = record(
        name="uvicorn.access",
        msg='%s - "%s %s HTTP/%s" %d',
        args=("10.0.0.1:5000", "GET", "/api/health", "1.1", 200),
    )

    entry = json.loads(JsonFormatter().format(rec))
    assert entry["event"] == "http_request"
    assert (entry["method"], entry["path"], entry["status"]) == ("GET", "/api/health", 200)


@pytest.fixture
def restore_logging():
    root = logging.getLogger()
    handlers, level = list(root.handlers), root.level
    uvicorn = logging.getLogger("uvicorn")
    uvicorn_state = (list(uvicorn.handlers), uvicorn.propagate)
    yield
    root.handlers[:] = handlers
    root.setLevel(level)
    uvicorn.handlers[:], uvicorn.propagate = uvicorn_state


def test_configure_logging_is_idempotent_and_keeps_foreign_handlers(restore_logging, capsys):
    root = logging.getLogger()
    foreign = logging.NullHandler()
    root.addHandler(foreign)
    logging.getLogger("uvicorn").addHandler(logging.StreamHandler())

    configure_logging("WARNING")
    configure_logging("info")

    assert foreign in root.handlers
    assert len([h for h in root.handlers if isinstance(h.formatter, JsonFormatter)]) == 1
    assert root.level == logging.INFO
    assert logging.getLogger("uvicorn").handlers == []
    assert logging.getLogger("uvicorn").propagate is True
    logging.getLogger("kupto.test").info("start", extra={"event": "x"})
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1])["event"] == "x"

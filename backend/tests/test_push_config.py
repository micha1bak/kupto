import logging

import pytest

from kupto.config import Settings
from kupto.push.keys import b64url_decode, generate
from kupto.push.notification import Notification, NotificationType
from kupto.push.vapid import VapidConfig

PUBLIC, PRIVATE = generate()
OTHER_PUBLIC, _ = generate()
SUBJECT = "https://kupto.example"


def settings(**vapid: str) -> Settings:
    return Settings(jwt_secret="x" * 32, **{f"vapid_{k}": v for k, v in vapid.items()})


def test_generated_keys_have_browser_format():
    assert len(b64url_decode(PUBLIC)) == 65 and b64url_decode(PUBLIC)[0] == 4
    assert len(b64url_decode(PRIVATE)) == 32
    assert "=" not in PUBLIC + PRIVATE


def test_valid_configuration_enables_push():
    config = VapidConfig.from_settings(
        settings(public_key=PUBLIC, private_key=PRIVATE, subject=SUBJECT)
    )

    assert config is not None
    assert config.public_key == PUBLIC
    assert config.subject == SUBJECT


def test_missing_keys_disable_push_quietly(caplog):
    with caplog.at_level(logging.INFO):
        assert VapidConfig.from_settings(settings()) is None
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]


@pytest.mark.parametrize(
    "vapid",
    [
        {"public_key": PUBLIC, "private_key": PRIVATE},
        {"public_key": OTHER_PUBLIC, "private_key": PRIVATE, "subject": SUBJECT},
        {"public_key": PUBLIC, "private_key": "nie-klucz", "subject": SUBJECT},
        {"public_key": PUBLIC, "private_key": PRIVATE, "subject": "kupto.example"},
    ],
    ids=["niekompletne", "niepasujace", "zly-prywatny", "zly-subject"],
)
def test_invalid_configuration_disables_push_with_error(caplog, vapid):
    with caplog.at_level(logging.ERROR):
        assert VapidConfig.from_settings(settings(**vapid)) is None
    assert caplog.records
    # Sekret nie trafia do logów.
    assert PRIVATE not in caplog.text


def test_payload_and_topic():
    notification = Notification(
        NotificationType.SHOPPING_STARTED, "Zakupy", "ala idzie do sklepu", tag="shopping-1"
    )

    assert notification.payload() == (
        '{"type": "shopping_started", "title": "Zakupy", "body": "ala idzie do sklepu", '
        '"url": "/", "tag": "shopping-1"}'
    )
    assert notification.topic == "shopping-1"
    assert Notification(NotificationType.ITEMS_ADDED, "a", "b", tag="ma spacje").topic is None
    assert Notification(NotificationType.ITEMS_ADDED, "a", "b", tag="x" * 33).topic is None

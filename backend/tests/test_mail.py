"""Backendy wysyłki maili (#77, design D7, D8)."""

import logging

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from kupto.config import Settings
from kupto.mail import (
    EmailMessage,
    LogMailSender,
    SesMailSender,
    mail_sender_from_settings,
    send_safely,
)
from kupto.main import create_app

MESSAGE = EmailMessage(
    to="ala@example.com",
    subject="Potwierdź adres e-mail w Kupto",
    body="Link: https://kupto.example/verify-email#token=TAJNY-TOKEN",
    kind="verify_email",
)


def settings(**overrides) -> Settings:
    return Settings(jwt_secret="unit-test-secret-that-is-long-enough", **overrides)


async def test_log_backend_does_not_log_address_or_link(caplog):
    caplog.set_level(logging.DEBUG, logger="kupto.mail")
    sender = LogMailSender()

    await sender.send(MESSAGE)

    assert sender.delivers is False
    assert "TAJNY-TOKEN" not in caplog.text
    assert "ala@example.com" not in caplog.text
    assert [r.event for r in caplog.records] == ["mail_not_sent"]


async def test_dev_log_backend_logs_link_at_info(caplog):
    caplog.set_level(logging.INFO, logger="kupto.mail")
    sender = LogMailSender(log_links=True)

    await sender.send(MESSAGE)

    assert sender.delivers is True
    (record,) = caplog.records
    assert record.levelno == logging.INFO
    assert "TAJNY-TOKEN" in record.getMessage()


class FakeSes:
    def __init__(self, error: Exception | None = None):
        self.calls: list[dict] = []
        self.error = error

    def send_email(self, **kwargs):
        if self.error:
            raise self.error
        self.calls.append(kwargs)
        return {"MessageId": "1"}


async def test_ses_backend_sends_plain_text_via_sesv2():
    client = FakeSes()
    sender = SesMailSender("Kupto <no-reply@kupto.example>", "eu-north-1", client=client)

    await sender.send(MESSAGE)

    (call,) = client.calls
    assert call["FromEmailAddress"] == "Kupto <no-reply@kupto.example>"
    assert call["Destination"] == {"ToAddresses": ["ala@example.com"]}
    simple = call["Content"]["Simple"]
    assert simple["Subject"]["Data"] == MESSAGE.subject
    assert simple["Body"]["Text"] == {"Data": MESSAGE.body, "Charset": "UTF-8"}


async def test_send_failure_is_logged_without_address_or_content(caplog):
    caplog.set_level(logging.INFO, logger="kupto.mail")
    error = RuntimeError("MessageRejected: Email address is not verified: ala@example.com")
    sender = SesMailSender("no-reply@kupto.example", "eu-north-1", client=FakeSes(error))

    await send_safely(sender, MESSAGE)

    assert [r.event for r in caplog.records] == ["mail_failed"]
    assert "ala@example.com" not in caplog.text
    assert "TAJNY-TOKEN" not in caplog.text


@pytest.mark.parametrize(
    "overrides, expected, delivers",
    [
        ({}, LogMailSender, False),
        ({"mail_log_links": True}, LogMailSender, True),
        ({"mail_backend": "ses", "mail_from": "no-reply@kupto.example"}, SesMailSender, True),
        # SES bez nadawcy: wysyłka wyłączona zamiast błędu przy starcie.
        ({"mail_backend": "ses"}, LogMailSender, False),
    ],
)
def test_backend_is_chosen_from_settings(overrides, expected, delivers):
    sender = mail_sender_from_settings(settings(**overrides))

    assert type(sender) is expected
    assert sender.delivers is delivers


@pytest.mark.parametrize(
    "domain, url",
    [("", "http://localhost:5173"), ("kupto.bakweb.pl", "https://kupto.bakweb.pl")],
)
def test_links_use_kupto_domain(domain, url):
    assert settings(kupto_domain=domain).app_url == url


async def test_production_logs_contain_no_tokens(migrated_database, caplog):
    """Domyślna konfiguracja (MAIL_BACKEND=log bez MAIL_LOG_LINKS) — jak produkcja przed SES."""
    caplog.set_level(logging.DEBUG)
    app = create_app(
        Settings(
            database_url=migrated_database,
            jwt_secret="test-secret-that-is-long-enough-for-hs256",
            cookie_secure=False,
        )
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/auth/register",
            json={"email": "logi@example.com", "password": "haslo1234", "name": "Logi"},
        )
    await app.state.list_events.close()
    await app.state.notifier.aclose()
    async with app.state.sessionmaker() as session:
        await session.execute(text("DELETE FROM users WHERE email = 'logi@example.com'"))
        await session.execute(text("DELETE FROM auth_rate_events"))
        await session.commit()
    await app.state.sessionmaker.kw["bind"].dispose()

    assert response.status_code == 201
    assert "#token=" not in caplog.text
    assert "logi@example.com" not in caplog.text

"""Wysyłka maili (#77): abstrakcja `MailSender` i jej implementacje (design D7, D8).

- `LogMailSender` — nic nie wysyła; domyślny backend (`MAIL_BACKEND=log`) w dev, testach i na
  produkcji przed konfiguracją SES. Treść (z linkami i tokenami) loguje tylko z
  `MAIL_LOG_LINKS=true`, czyli wyłącznie w dev — wtedy też udaje działającą wysyłkę.
- `SesMailSender` — Amazon SES przez API v2 (boto3), poświadczenia z roli instancji EC2.

`delivers` mówi, czy użytkownik faktycznie dostanie link; od tego zależy, czy aplikacja
wymaga potwierdzenia adresu i czy przyjmuje prośby o reset hasła.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Protocol

from kupto.config import Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    body: str  # zwykły tekst
    # Rodzaj maila do logów (np. `verify_email`) — bez adresu i treści.
    kind: str


class MailSender(Protocol):
    delivers: bool

    async def send(self, message: EmailMessage) -> None:
        """Wysyła mail albo zgłasza wyjątek (wołający loguje go bez treści maila)."""
        ...


class LogMailSender:
    def __init__(self, log_links: bool = False):
        self.log_links = log_links
        self.delivers = log_links

    async def send(self, message: EmailMessage) -> None:
        if self.log_links:
            logger.info(
                "Mail (dev, bez wysyłki) do %s: %s\n%s",
                message.to,
                message.subject,
                message.body,
                extra={"event": "mail_logged", "kind": message.kind},
            )
            return
        # Produkcja bez SES: bez adresu i treści — link zawiera jednorazowy token.
        logger.info(
            "Wysyłka maili wyłączona (MAIL_BACKEND=log) — mail „%s” nie został wysłany.",
            message.subject,
            extra={"event": "mail_not_sent", "kind": message.kind},
        )


class SesMailSender:
    delivers = True

    def __init__(self, sender: str, region: str, client: Any | None = None):
        self.sender = sender
        self.region = region
        self._client = client  # testy podają atrapę; inaczej klient tworzony leniwie

    def _get_client(self) -> Any:
        if self._client is None:
            import boto3  # import leniwy: boto3 ładuje się kilkaset ms, a w dev zwykle zbędny

            self._client = boto3.client("sesv2", region_name=self.region)
        return self._client

    def _send(self, message: EmailMessage) -> None:
        self._get_client().send_email(
            FromEmailAddress=self.sender,
            Destination={"ToAddresses": [message.to]},
            Content={
                "Simple": {
                    "Subject": {"Data": message.subject, "Charset": "UTF-8"},
                    "Body": {"Text": {"Data": message.body, "Charset": "UTF-8"}},
                }
            },
        )

    async def send(self, message: EmailMessage) -> None:
        await asyncio.to_thread(self._send, message)
        logger.info(
            "Wysłano mail „%s”.",
            message.subject,
            extra={"event": "mail_sent", "kind": message.kind},
        )


def mail_sender_from_settings(settings: Settings) -> MailSender:
    """Backend z konfiguracji; błędna konfiguracja SES wyłącza wysyłkę zamiast zatrzymać start."""
    if settings.mail_backend == "ses":
        sender = settings.mail_from.strip()
        if not sender:
            logger.error("Wysyłka maili wyłączona: MAIL_BACKEND=ses wymaga ustawienia MAIL_FROM.")
            return LogMailSender()
        logger.info("Wysyłka maili przez Amazon SES (%s).", settings.mail_ses_region)
        return SesMailSender(sender, settings.mail_ses_region)
    if settings.mail_log_links:
        logger.warning(
            "MAIL_LOG_LINKS=true: treść maili z linkami trafia do logów — tylko do rozwoju."
        )
        return LogMailSender(log_links=True)
    logger.info(
        "Wysyłka maili wyłączona (MAIL_BACKEND=log): weryfikacja adresów nie jest wymagana."
    )
    return LogMailSender()


async def send_safely(sender: MailSender, message: EmailMessage) -> None:
    """Wysyłka w tle (po odpowiedzi): błąd trafia do logu bez adresu i treści maila."""
    try:
        await sender.send(message)
    except Exception as exc:
        # Bez `exc_info`: komunikat wyjątku boto3 może zawierać adres odbiorcy.
        logger.error(
            "Nie udało się wysłać maila „%s”: %s",
            message.subject,
            type(exc).__name__,
            extra={"event": "mail_failed", "kind": message.kind},
        )

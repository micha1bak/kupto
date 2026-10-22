"""Subskrypcje Web Push urządzeń użytkowników (design D3, D4)."""

from urllib.parse import urlsplit

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from kupto.db import utcnow
from kupto.models import PushSubscription, User

MAX_ENDPOINT_LENGTH = 2048
MAX_USER_AGENT_LENGTH = 300
MAX_SUBSCRIPTIONS_PER_USER = 10

# Serwer wysyła żądania pod adres podany przez klienta, więc przyjmujemy tylko usługi push
# przeglądarek (ochrona przed SSRF). Nowa przeglądarka z inną usługą = dopisanie domeny.
PUSH_SERVICE_DOMAINS = (
    "googleapis.com",  # Chrome, Android, Opera, Samsung Internet (FCM)
    "mozilla.com",  # Firefox
    "push.apple.com",  # Safari na macOS i iOS
    "notify.windows.com",  # Edge (WNS)
)


def validate_endpoint(endpoint: str) -> str:
    """Zwraca endpoint, jeśli to adres HTTPS znanej usługi push; inaczej ValueError."""
    try:
        parts = urlsplit(endpoint)
        port = parts.port
    except ValueError as exc:
        raise ValueError("Nieprawidłowy adres usługi powiadomień.") from exc
    host = (parts.hostname or "").lower()
    if (
        parts.scheme != "https"
        or not host
        or port is not None
        or parts.username is not None
        or parts.password is not None
        or not any(host == d or host.endswith(f".{d}") for d in PUSH_SERVICE_DOMAINS)
    ):
        raise ValueError("Ta przeglądarka używa nieobsługiwanej usługi powiadomień.")
    return endpoint


async def save(
    session: AsyncSession,
    user: User,
    *,
    endpoint: str,
    p256dh: str,
    auth: str,
    user_agent: str | None,
) -> None:
    """Zapisuje subskrypcję urządzenia albo przepina istniejącą (ten sam endpoint) na `user`.

    Ponad `MAX_SUBSCRIPTIONS_PER_USER` usuwane są najdawniej odświeżone subskrypcje użytkownika.
    """
    now = utcnow()
    values = {
        "user_id": user.id,
        "p256dh": p256dh,
        "auth": auth,
        "user_agent": user_agent[:MAX_USER_AGENT_LENGTH] if user_agent else None,
        "updated_at": now,
    }
    await session.execute(
        insert(PushSubscription)
        .values(endpoint=endpoint, created_at=now, **values)
        .on_conflict_do_update(index_elements=[PushSubscription.endpoint], set_=values)
    )
    newest = (
        select(PushSubscription.id)
        .where(PushSubscription.user_id == user.id)
        .order_by(PushSubscription.updated_at.desc(), PushSubscription.id.desc())
        .limit(MAX_SUBSCRIPTIONS_PER_USER)
    )
    await session.execute(
        delete(PushSubscription).where(
            PushSubscription.user_id == user.id, PushSubscription.id.not_in(newest)
        )
    )
    await session.commit()


async def remove(session: AsyncSession, user: User, endpoint: str) -> None:
    """Usuwa subskrypcję urządzenia, jeśli należy do `user` (cudzej nie rusza)."""
    await session.execute(
        delete(PushSubscription).where(
            PushSubscription.user_id == user.id, PushSubscription.endpoint == endpoint
        )
    )
    await session.commit()

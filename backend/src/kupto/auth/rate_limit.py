"""Limity prób rejestracji, resetu hasła i wysyłki linków (#77, design D5).

Zdarzenia leżą w bazie (`auth_rate_events`), więc limit przeżywa restart i działa przy wielu
workerach. Klucz (adres, IP, id konta) jest zapisywany tylko jako skrót.
"""

import hashlib
import math
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from kupto.db import utcnow
from kupto.errors import TooManyRequests
from kupto.models import AuthRateEvent

WINDOW = timedelta(hours=1)
_RETENTION = timedelta(days=1)


@dataclass(frozen=True)
class Limit:
    action: str
    per_hour: int


REGISTER_PER_IP = Limit("register_ip", 5)
PASSWORD_RESET_PER_EMAIL = Limit("password_reset_email", 3)
PASSWORD_RESET_PER_IP = Limit("password_reset_ip", 10)
VERIFICATION_PER_USER = Limit("verification_user", 5)
VERIFICATION_PER_EMAIL = Limit("verification_email", 3)


def _key_hash(limit: Limit, key: str) -> str:
    return hashlib.sha256(f"{limit.action}:{key}".encode()).hexdigest()


async def check(session: AsyncSession, *checks: tuple[Limit, str]) -> None:
    """Sprawdza wszystkie limity i, jeśli żaden nie jest przekroczony, liczy próbę w każdym.

    Przekroczenie: 429 z `Retry-After` (do wygaśnięcia najstarszej próby w oknie), bez zapisu
    — odrzucone próby nie wydłużają blokady. Zdarzenia są zatwierdzane od razu, niezależnie od
    dalszego losu żądania (np. nieistniejącego konta przy resecie hasła).
    """
    now = utcnow()
    window_start = now - WINDOW
    for limit, key in checks:
        count, oldest = (
            await session.execute(
                select(func.count(AuthRateEvent.id), func.min(AuthRateEvent.created_at)).where(
                    AuthRateEvent.action == limit.action,
                    AuthRateEvent.key_hash == _key_hash(limit, key),
                    AuthRateEvent.created_at > window_start,
                )
            )
        ).one()
        if count >= limit.per_hour:
            retry_after = max(1, math.ceil((oldest - window_start).total_seconds()))
            raise TooManyRequests(
                f"Zbyt wiele prób. Spróbuj ponownie za {math.ceil(retry_after / 60)} min.",
                retry_after=retry_after,
            )
    for limit, key in checks:
        await session.execute(
            delete(AuthRateEvent).where(
                AuthRateEvent.action == limit.action, AuthRateEvent.created_at < now - _RETENTION
            )
        )
        session.add(
            AuthRateEvent(action=limit.action, key_hash=_key_hash(limit, key), created_at=now)
        )
    await session.commit()

"""Limity prób rejestracji, resetu hasła i wysyłki linków (#77, design D5).

Zdarzenia leżą w bazie (`auth_rate_events`), więc limit przeżywa restart i działa przy wielu
workerach. Klucz (adres, IP, id konta) jest zapisywany tylko jako skrót.
"""

import hashlib
import math
import random
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from kupto.db import utcnow
from kupto.errors import TooManyRequests
from kupto.models import AuthRateEvent

WINDOW = timedelta(hours=1)
_RETENTION = timedelta(days=1)
CLEANUP_EVERY = 100


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


def _lock_id(key_hash: str) -> int:
    # 64-bitowy klucz blokady doradczej z początku skrótu (zakres bigint ze znakiem).
    return int.from_bytes(bytes.fromhex(key_hash[:16]), "big", signed=True)


async def check(session: AsyncSession, *checks: tuple[Limit, str]) -> None:
    """Sprawdza wszystkie limity i, jeśli żaden nie jest przekroczony, liczy próbę w każdym.

    Sprawdzenie i zapis są atomowe: blokada doradcza transakcji (`pg_advisory_xact_lock`) na
    skrócie każdego klucza szereguje równoległe żądania z tym samym kluczem aż do zatwierdzenia,
    więc N równoległych prób nie przejdzie limitu. Blokady w stałej kolejności — bez zakleszczeń.

    Przekroczenie: 429 z `Retry-After` (do wygaśnięcia najstarszej próby w oknie), bez zapisu
    — odrzucone próby nie wydłużają blokady. Zdarzenia są zatwierdzane od razu, niezależnie od
    dalszego losu żądania (np. nieistniejącego konta przy resecie hasła).
    """
    hashed = [(limit, _key_hash(limit, key)) for limit, key in checks]
    for lock in sorted({_lock_id(key_hash) for _, key_hash in hashed}):
        await session.execute(select(func.pg_advisory_xact_lock(lock)))
    now = utcnow()
    window_start = now - WINDOW
    for limit, key_hash in hashed:
        count, oldest = (
            await session.execute(
                select(func.count(AuthRateEvent.id), func.min(AuthRateEvent.created_at)).where(
                    AuthRateEvent.action == limit.action,
                    AuthRateEvent.key_hash == key_hash,
                    AuthRateEvent.created_at > window_start,
                )
            )
        ).one()
        if count >= limit.per_hour:
            await session.rollback()  # zwalnia blokady
            retry_after = max(1, math.ceil((oldest - window_start).total_seconds()))
            raise TooManyRequests(
                f"Zbyt wiele prób. Spróbuj ponownie za {math.ceil(retry_after / 60)} min.",
                retry_after=retry_after,
            )
    session.add_all(
        AuthRateEvent(action=limit.action, key_hash=key_hash, created_at=now)
        for limit, key_hash in hashed
    )
    # Sprzątanie starych zdarzeń (indeks na `created_at`) średnio raz na CLEANUP_EVERY zapisów —
    # nie przy każdym żądaniu; zdarzenia spoza okna i tak nie są liczone.
    if random.random() < 1 / CLEANUP_EVERY:
        await session.execute(
            delete(AuthRateEvent).where(AuthRateEvent.created_at < now - _RETENTION)
        )
    await session.commit()

"""Jednorazowe tokeny z linków w mailach (#77, design D2).

Token ma 256 bitów losowości i trafia tylko do maila; w bazie leży jego skrót SHA-256, więc
wyciek bazy nie daje działających linków. Ważny jest tylko najnowszy token danego rodzaju.
"""

import hashlib
import secrets
from datetime import timedelta

from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from kupto.db import utcnow
from kupto.models import AuthToken, User

VERIFY_EMAIL = "verify_email"
RESET_PASSWORD = "reset_password"


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def issue(session: AsyncSession, user: User, purpose: str, email: str, ttl: timedelta) -> str:
    """Nowy token (zwracany otwartym tekstem do linku); poprzednie niewykorzystane tokeny tego
    rodzaju dla konta przestają działać. Zapis zatwierdza wołający."""
    await session.execute(
        delete(AuthToken).where(
            AuthToken.user_id == user.id,
            AuthToken.purpose == purpose,
            AuthToken.used_at.is_(None),
        )
    )
    token = secrets.token_urlsafe(32)
    now = utcnow()
    session.add(
        AuthToken(
            user_id=user.id,
            purpose=purpose,
            token_hash=token_hash(token),
            email=email,
            created_at=now,
            expires_at=now + ttl,
        )
    )
    return token


async def consume(session: AsyncSession, token: str, purpose: str) -> AuthToken | None:
    """Zużywa ważny token (atomowo — dwa równoległe kliknięcia nie użyją go dwa razy).

    `None` dla nieznanego, wygasłego, użytego lub innego rodzaju tokenu — wołający odpowiada
    w każdym z tych przypadków tak samo. Zapis zatwierdza wołający.
    """
    if not token or len(token) > 200:
        return None
    now = utcnow()
    return await session.scalar(
        update(AuthToken)
        .where(
            AuthToken.token_hash == token_hash(token),
            AuthToken.purpose == purpose,
            AuthToken.used_at.is_(None),
            AuthToken.expires_at > now,
        )
        .values(used_at=now)
        .returning(AuthToken)
    )

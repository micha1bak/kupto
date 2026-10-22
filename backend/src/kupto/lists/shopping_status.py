"""Status „robię zakupy” członków gospodarstwa.

Status to jeden znacznik czasu przy użytkowniku (`User.shopping_since`). Wygasa sam po
`SHOPPING_STATUS_TTL` — liczone przy każdym odczycie, bez zadań w tle; przeterminowana wartość
może zostać w bazie, ale żaden odczyt jej nie uznaje. Dlatego aktywność statusu należy oceniać
wyłącznie funkcjami z tego modułu.

Punkt odczytu dla powiadomień:
- `start` / `stop` zwracają, czy status faktycznie się zmienił (powiadomienie tylko przy zmianie),
- `active_shoppers` mówi, kto w gospodarstwie robi teraz zakupy i od kiedy.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from kupto.db import utcnow
from kupto.models import Household, User

SHOPPING_STATUS_TTL = timedelta(hours=3)


@dataclass(frozen=True)
class Shopper:
    user_id: int
    login: str
    since: datetime
    expires_at: datetime


def expires_at(since: datetime) -> datetime:
    return since + SHOPPING_STATUS_TTL


def _active(now: datetime):
    return User.shopping_since > now - SHOPPING_STATUS_TTL


async def start(session: AsyncSession, user: User, now: datetime | None = None) -> bool:
    """Włącza status; zwraca True, jeśli właśnie się zaczął (False — był już aktywny).

    Aktywnego statusu nie odnawia, żeby „od kiedy” zostało prawdziwe. Warunkowy UPDATE sprawia,
    że z dwóch równoległych wywołań tylko jedno zwróci True.
    """
    now = now or utcnow()
    started = await session.scalar(
        update(User)
        .where(User.id == user.id, or_(User.shopping_since.is_(None), ~_active(now)))
        .values(shopping_since=now)
        .returning(User.id)
    )
    await session.commit()
    await session.refresh(user, ["shopping_since"])
    return started is not None


async def stop(session: AsyncSession, user: User, now: datetime | None = None) -> bool:
    """Wyłącza status; zwraca True, jeśli był aktywny."""
    was_active = await clear(session, user, now)
    await session.commit()
    return was_active


async def clear(session: AsyncSession, user: User, now: datetime | None = None) -> bool:
    """Jak `stop`, ale bez commitu — do użycia w transakcji innej operacji.

    Np. zakończenie zakupów albo odejście z gospodarstwa zdejmują status razem ze swoją zmianą.
    """
    now = now or utcnow()
    was_active = await session.scalar(
        select(_active(now)).select_from(User).where(User.id == user.id)
    )
    await session.execute(
        update(User).where(User.id == user.id).values(shopping_since=None),
        execution_options={"synchronize_session": False},
    )
    user.shopping_since = None
    return bool(was_active)


async def active_shoppers(
    session: AsyncSession, household: Household, now: datetime | None = None
) -> list[Shopper]:
    """Członkowie gospodarstwa z aktywnym statusem, najdawniej rozpoczęty pierwszy."""
    now = now or utcnow()
    rows = await session.execute(
        select(User.id, User.login, User.shopping_since)
        .where(User.household_id == household.id, _active(now))
        .order_by(User.shopping_since, User.id)
    )
    return [
        Shopper(user_id=uid, login=login, since=since, expires_at=expires_at(since))
        for uid, login, since in rows
    ]

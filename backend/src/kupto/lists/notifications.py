"""Powiadomienia push o zakupach (#29–#31).

Każda funkcja jest wołana PO commicie zmiany, która ją wywołała: buduje treść z aktualnego
stanu bazy i planuje wysyłkę (`Notifier` wysyła w tle). Treść zawiera tylko imiona i nazwy
produktów z listy gospodarstwa — nic, czego domownicy nie widzą w aplikacji.
"""

import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from functools import wraps

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from kupto.db import utcnow
from kupto.lists import shopping_status
from kupto.models import Household, ListItem, Need, ShoppingList, User, display_name
from kupto.push.notification import Notification, NotificationType
from kupto.push.notifier import Notifier

logger = logging.getLogger(__name__)

# Ile nazw produktów pokazujemy w treści; reszta jako „i N innych”.
MAX_NAMES = 5
MAX_NAME_LENGTH = 40
# „Dopisano w trakcie”: produkty dopisane w tym oknie (nie wcześniej niż od początku statusu)
# trafiają do jednego, aktualizowanego powiadomienia (stały tag per kupujący).
ITEMS_ADDED_WINDOW = timedelta(minutes=10)


def _best_effort[**P](notify: Callable[P, Awaitable[None]]) -> Callable[P, Awaitable[None]]:
    """Zmiana jest już zapisana — błąd przygotowania powiadomienia nie może zepsuć odpowiedzi."""

    @wraps(notify)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> None:
        try:
            await notify(*args, **kwargs)
        except Exception:
            logger.exception("Nie udało się przygotować powiadomienia (%s).", notify.__name__)

    return wrapper


def format_names(names: list[str]) -> str:
    """„mleko, chleb i 3 inne” — najwyżej `MAX_NAMES` nazw, każda przycięta."""
    shown = [_shorten(name) for name in names[:MAX_NAMES]]
    rest = len(names) - len(shown)
    if rest <= 0:
        return ", ".join(shown)
    return f"{', '.join(shown)} i {rest} {_others(rest)}"


def _shorten(name: str) -> str:
    return name if len(name) <= MAX_NAME_LENGTH else name[: MAX_NAME_LENGTH - 1].rstrip() + "…"


def _others(count: int) -> str:
    if count == 1:
        return "inny"
    if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        return "inne"
    return "innych"


def shopping_started_tag(household_id: int) -> str:
    return f"shopping-started-{household_id}"


def items_added_tag(household_id: int, user_id: int) -> str:
    return f"items-added-{household_id}-{user_id}"


def shopping_finished_tag(household_id: int) -> str:
    return f"shopping-finished-{household_id}"


def shopping_started(notifier: Notifier, household: Household, shopper: User) -> None:
    """#29: pozostali domownicy dostają „{imię} idzie na zakupy”. Wołać tylko, gdy `start`
    zwrócił True (status faktycznie się zaczął)."""
    notifier.send_to_household(
        household.id,
        Notification(
            NotificationType.SHOPPING_STARTED,
            title=f"{display_name(shopper)} idzie na zakupy",
            body="Dopisz, czego potrzebujesz.",
            tag=shopping_started_tag(household.id),
        ),
        exclude_user_ids={shopper.id},
    )


@_best_effort
async def items_added(
    session: AsyncSession,
    notifier: Notifier,
    household: Household,
    author: User,
    now: datetime | None = None,
) -> None:
    """#30: kupujący (poza autorem) dostają listę produktów dopisanych w trakcie ich zakupów.

    Bez stanu w pamięci: treść to wszystkie niekupione pozycje z zapotrzebowaniami innych osób
    dopisanymi w ostatnim `ITEMS_ADDED_WINDOW` (nie wcześniej niż od początku statusu), a stały
    tag sprawia, że kolejne dopisanie zastępuje poprzednie powiadomienie na urządzeniu.
    """
    now = now or utcnow()
    shoppers = [
        s
        for s in await shopping_status.active_shoppers(session, household, now)
        if s.user_id != author.id
    ]
    for shopper in shoppers:
        names = await _recently_added(session, household, shopper.user_id, shopper.since, now)
        if not names:
            continue
        notifier.send_to_users(
            [shopper.user_id],
            Notification(
                NotificationType.ITEMS_ADDED,
                title="Dopisano w trakcie zakupów",
                body=format_names(names),
                tag=items_added_tag(household.id, shopper.user_id),
                ttl=int(ITEMS_ADDED_WINDOW.total_seconds()) * 3,
                urgency="high",
            ),
        )


@_best_effort
async def shopping_finished(
    session: AsyncSession, notifier: Notifier, household: Household, shopper: User
) -> None:
    """#31: pozostali domownicy dostają „{imię}: zakupy zakończone” z tym, czego zabrakło
    (niekupione pozycje, które zostały na liście). Wołać po zakończeniu z przeniesionymi
    pozycjami."""
    remaining = list(
        await session.scalars(
            select(ListItem.name)
            .join(ShoppingList)
            .where(ShoppingList.household_id == household.id, ListItem.bought_at.is_(None))
            .order_by(ListItem.created_at, ListItem.id)
        )
    )
    body = f"Nie było: {format_names(remaining)}." if remaining else "Wszystko kupione."
    notifier.send_to_household(
        household.id,
        Notification(
            NotificationType.SHOPPING_FINISHED,
            title=f"{display_name(shopper)}: zakupy zakończone",
            body=body,
            tag=shopping_finished_tag(household.id),
        ),
        exclude_user_ids={shopper.id},
    )


async def _recently_added(
    session: AsyncSession, household: Household, shopper_id: int, since: datetime, now: datetime
) -> list[str]:
    """Niekupione pozycje z zapotrzebowaniami innych niż kupujący, najnowsze pierwsze."""
    window_start = max(since, now - ITEMS_ADDED_WINDOW)
    latest = func.max(Need.created_at)
    rows = await session.execute(
        select(ListItem.name, latest)
        .join(Need, Need.item_id == ListItem.id)
        .join(ShoppingList)
        .where(
            ShoppingList.household_id == household.id,
            ListItem.bought_at.is_(None),
            Need.user_id != shopper_id,
            Need.created_at >= window_start,
        )
        .group_by(ListItem.id, ListItem.name)
        .order_by(latest.desc(), ListItem.id.desc())
    )
    return [name for name, _ in rows]

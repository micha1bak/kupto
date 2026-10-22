"""Przypomnienia push o zwykłych produktach (#40, change `usual-reminders`).

    python -m kupto.history.reminders

Uruchamiane raz dziennie przez `kupto-reminders.timer` (deploy/) w kontenerze backendu.
Produkty pochodzą z `usual_missing` (#39). Limity pilnuje kod, nie harmonogram (design D2):

1. Wysyłka tylko między `SEND_FROM` a `SEND_UNTIL` czasu polskiego.
2. Najwyżej jedno przypomnienie na gospodarstwo na dobę czasu polskiego.
3. Tylko gdy co najmniej jeden produkt jest *nowy*: gospodarstwo nie dostało o nim
   przypomnienia albo kupiło go po ostatnim przypomnieniu (`usual_reminders.reminded_at`).

Decyzja i zapis odbywają się w transakcji z blokadą wiersza gospodarstwa, a wysyłka dopiero po
commicie — równoległe uruchomienia nie dublują przypomnień, a błąd wysyłki ich nie ponawia.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import delete, exists, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kupto.config import Settings, get_settings
from kupto.db import create_sessionmaker, utcnow
from kupto.history.usual import HISTORY_WINDOW, Suggestion, usual_missing
from kupto.lists.notifications import format_names
from kupto.logs import configure_logging
from kupto.models import Household, PushSubscription, User, UsualReminder
from kupto.push import preferences
from kupto.push.notification import Notification, NotificationType
from kupto.push.notifier import Notifier, PushTransport

logger = logging.getLogger(__name__)

TIMEZONE = ZoneInfo("Europe/Warsaw")
SEND_FROM = time(9)
SEND_UNTIL = time(21)
# Niedoręczone w ciągu kilku godzin przypomnienie traci sens (i nie powinno przyjść w nocy).
REMINDER_TTL_SECONDS = 4 * 3600


@dataclass(frozen=True)
class Reminder:
    """Przypomnienie przygotowane (i zapisane) dla jednego gospodarstwa."""

    household_id: int
    user_ids: frozenset[int]
    names: list[str]  # nowe produkty pierwsze

    def notification(self) -> Notification:
        return Notification(
            NotificationType.USUAL_REMINDER,
            title="Zwykle o tej porze kupujecie",
            body=f"{format_names(self.names)} — dopisać do listy?",
            url="/",
            tag=reminder_tag(self.household_id),
            ttl=REMINDER_TTL_SECONDS,
        )


def reminder_tag(household_id: int) -> str:
    return f"usual-reminder-{household_id}"


def local_date(moment: datetime) -> date:
    return moment.astimezone(TIMEZONE).date()


def in_send_window(now: datetime) -> bool:
    return SEND_FROM <= now.astimezone(TIMEZONE).time() < SEND_UNTIL


def is_new(suggestion: Suggestion, reminded: dict[str, datetime]) -> bool:
    """Produkt nieprzypominany albo kupiony po ostatnim przypomnieniu o nim."""
    reminded_at = reminded.get(suggestion.normalized_name)
    return reminded_at is None or reminded_at < suggestion.last_bought_at


async def send_reminders(
    sessionmaker: async_sessionmaker[AsyncSession], notifier: Notifier, now: datetime | None = None
) -> int:
    """Przypomnienia dla wszystkich gospodarstw; zwraca liczbę gospodarstw, do których poszły."""
    now = now or utcnow()
    if not notifier.enabled:
        logger.info("Powiadomienia push wyłączone — pomijam przypomnienia o zwykłych produktach.")
        return 0
    if not in_send_window(now):
        logger.info(
            "Poza godzinami przypomnień (%s–%s czasu polskiego) — pomijam.", SEND_FROM, SEND_UNTIL
        )
        return 0

    async with sessionmaker() as session:
        household_ids = list(await session.scalars(select(Household.id).order_by(Household.id)))
    sent = 0
    for household_id in household_ids:
        try:
            async with sessionmaker() as session:
                reminder = await prepare_reminder(session, household_id, now)
            if reminder is None:
                continue
            await notifier.deliver_to_users(reminder.user_ids, reminder.notification())
            sent += 1
        except Exception:
            # Jedno gospodarstwo nie może zablokować przypomnień dla pozostałych.
            logger.exception(
                "Przypomnienie o zwykłych produktach nie powiodło się.",
                extra={"household_id": household_id},
            )
    logger.info(
        "Przypomnienia o zwykłych produktach: %s z %s gospodarstw.",
        sent,
        len(household_ids),
        extra={"event": "usual_reminders", "sent": sent, "households": len(household_ids)},
    )
    return sent


async def prepare_reminder(
    session: AsyncSession, household_id: int, now: datetime
) -> Reminder | None:
    """Wybiera produkty i zapisuje przypomnienie (commit); None — gospodarstwo pomijamy.

    Pominięcie niczego nie zapisuje, więc np. włączenie przypomnień po czasie obejmie też
    produkty, których brakowało już wcześniej.
    """
    household = await session.scalar(
        select(Household).where(Household.id == household_id).with_for_update()
    )
    if household is None:
        return None
    rows = await session.execute(
        select(UsualReminder.normalized_name, UsualReminder.reminded_at).where(
            UsualReminder.household_id == household_id
        )
    )
    reminded = {normalized: reminded_at for normalized, reminded_at in rows}
    if reminded and local_date(max(reminded.values())) == local_date(now):
        return None
    user_ids = await _recipients(session, household_id)
    if not user_ids:
        return None
    suggestions = await usual_missing(session, household, now)
    new = [s for s in suggestions if is_new(s, reminded)]
    if not new:
        return None

    mentioned = new + [s for s in suggestions if not is_new(s, reminded)]
    await session.execute(
        insert(UsualReminder)
        .values(
            [
                {
                    "household_id": household_id,
                    "normalized_name": s.normalized_name,
                    "reminded_at": now,
                }
                for s in mentioned
            ]
        )
        .on_conflict_do_update(
            index_elements=[UsualReminder.household_id, UsualReminder.normalized_name],
            set_={"reminded_at": now},
        )
    )
    # Starsze wpisy nie wpłyną już na wynik — `usual_missing` nie widzi tak starych zakupów.
    await session.execute(
        delete(UsualReminder).where(
            UsualReminder.household_id == household_id,
            UsualReminder.reminded_at < now - HISTORY_WINDOW,
        )
    )
    await session.commit()
    return Reminder(household_id, frozenset(user_ids), [s.name for s in mentioned])


async def _recipients(session: AsyncSession, household_id: int) -> set[int]:
    """Członkowie z włączonym typem przypomnień i co najmniej jednym urządzeniem."""
    members = await session.scalars(
        select(User.id).where(
            User.household_id == household_id,
            exists().where(PushSubscription.user_id == User.id),
        )
    )
    return await preferences.recipients_wanting(
        session, set(members), NotificationType.USUAL_REMINDER
    )


async def run(
    settings: Settings, transport: PushTransport | None = None, now: datetime | None = None
) -> int:
    sessionmaker = create_sessionmaker(settings.database_url)
    notifier = Notifier.from_settings(settings, sessionmaker, transport=transport)
    try:
        return await send_reminders(sessionmaker, notifier, now)
    finally:
        await notifier.aclose()
        await sessionmaker.kw["bind"].dispose()


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    asyncio.run(run(settings))


if __name__ == "__main__":
    main()

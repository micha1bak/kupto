"""Rozgłaszanie zmian listy i czatu gospodarstwa przez Postgres LISTEN/NOTIFY.

Publikacja (`list_changed`, `order_changed`, `member_left`, `chat_changed`) dokłada `pg_notify`
do bieżącej transakcji serwisu: Postgres dostarcza powiadomienie dopiero po commicie, a przy
rollbacku je odrzuca. Dzięki temu sygnał nigdy nie wyprzedza zmiany i działa przy wielu
instancjach backendu.

`ListEventBroker` trzyma w każdym procesie jedno połączenie `LISTEN` (poza pulą SQLAlchemy)
i rozprowadza sygnały do subskrypcji strumieni SSE danego gospodarstwa.
"""

import asyncio
import contextlib
import json
import logging
from typing import Literal

import asyncpg
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from kupto.models import User

CHANNEL = "kupto_list"
logger = logging.getLogger(__name__)

Kind = Literal["changed", "left", "chat"]
# Rodzaje sygnałów dostarczanych subskrypcji (zdarzenia SSE `list_changed` i `chat_changed`).
Signal = Literal["list", "chat"]


async def _notify(
    session: AsyncSession, household_id: int, user_id: int | None, kind: Kind
) -> None:
    payload = json.dumps({"household": household_id, "user": user_id, "kind": kind})
    await session.execute(select(func.pg_notify(CHANNEL, payload)))


async def list_changed(session: AsyncSession, household_id: int) -> None:
    """Wspólna lista gospodarstwa się zmieniła — sygnał dla wszystkich jego członków."""
    await _notify(session, household_id, None, "changed")


async def order_changed(session: AsyncSession, user: User) -> None:
    """Zmieniła się kolejność kategorii użytkownika — sygnał tylko dla jego strumieni."""
    if user.household_id is not None:
        await _notify(session, user.household_id, user.id, "changed")


async def chat_changed(session: AsyncSession, household_id: int) -> None:
    """W czacie gospodarstwa pojawiła się wiadomość — sygnał dla wszystkich jego członków (#78)."""
    await _notify(session, household_id, None, "chat")


async def member_left(session: AsyncSession, household_id: int, user_id: int) -> None:
    """Użytkownik przestał należeć do gospodarstwa — jego strumienie mają się zakończyć."""
    await _notify(session, household_id, user_id, "left")


class BrokerUnavailable(Exception):
    """Brak połączenia LISTEN — strumień nie gwarantowałby dostarczania zmian."""


class Subscription:
    """Subskrypcja jednego strumienia. Kolejne sygnały tego samego rodzaju łączą się w jeden
    (bez kolejki); rodzaje (lista, czat) dostarczane są osobno."""

    def __init__(self, household_id: int, user_id: int):
        self.household_id = household_id
        self.user_id = user_id
        self.closed = False
        self._changed = asyncio.Event()
        self._pending: set[Signal] = set()

    async def wait(self, seconds: float) -> frozenset[Signal]:
        """Czeka na zmianę i zwraca jej rodzaje; pusty zbiór po `seconds` bez zmian.
        Sprawdź potem `closed`."""
        try:
            await asyncio.wait_for(self._changed.wait(), seconds)
        except TimeoutError:
            return frozenset()
        self._changed.clear()
        signals = frozenset(self._pending)
        self._pending.clear()
        return signals

    def _signal(self, signal: Signal = "list") -> None:
        self._pending.add(signal)
        self._changed.set()

    def _close(self) -> None:
        self.closed = True
        self._changed.set()


class ListEventBroker:
    """Jedno połączenie LISTEN na proces, rozprowadzające sygnały do subskrybentów.

    Startuje leniwie przy pierwszym oczekiwaniu na gotowość. Utrata połączenia zamyka wszystkie
    subskrypcje: klienci łączą się ponownie i pobierają listę, więc żadna zmiana nie ginie
    po cichu, a otwarty strumień zawsze oznacza działające dostarczanie sygnałów.
    """

    def __init__(
        self,
        database_url: str,
        *,
        retry_delay: float = 2.0,
        health_check_seconds: float = 30.0,
    ):
        url = make_url(database_url).set(drivername="postgresql")
        self._dsn = url.render_as_string(hide_password=False)
        self._retry_delay = retry_delay
        self._health_check_seconds = health_check_seconds
        self._subscriptions: dict[int, set[Subscription]] = {}
        self._ready = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._closing = False

    @property
    def subscription_count(self) -> int:
        return sum(len(subs) for subs in self._subscriptions.values())

    async def wait_ready(self, seconds: float) -> None:
        """Uruchamia nasłuch (jeśli trzeba) i czeka do `seconds` na połączenie LISTEN."""
        if self._closing:
            raise BrokerUnavailable
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run(), name="kupto-list-events")
        try:
            await asyncio.wait_for(self._ready.wait(), seconds)
        except TimeoutError:
            raise BrokerUnavailable from None

    def subscribe(self, household_id: int, user_id: int) -> Subscription:
        if not self._ready.is_set():
            raise BrokerUnavailable
        subscription = Subscription(household_id, user_id)
        self._subscriptions.setdefault(household_id, set()).add(subscription)
        return subscription

    def unsubscribe(self, subscription: Subscription) -> None:
        subs = self._subscriptions.get(subscription.household_id)
        if subs is not None:
            subs.discard(subscription)
            if not subs:
                del self._subscriptions[subscription.household_id]

    async def close(self) -> None:
        self._closing = True
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        self._close_all()

    async def _run(self) -> None:
        while not self._closing:
            try:
                connection = await asyncpg.connect(self._dsn, timeout=10)
            except (OSError, TimeoutError, asyncpg.PostgresError) as exc:
                logger.warning("Brak połączenia LISTEN dla zmian listy: %s", exc)
                await asyncio.sleep(self._retry_delay)
                continue
            try:
                await self._listen(connection)
            except (OSError, TimeoutError, asyncpg.PostgresError) as exc:
                logger.warning("Utracono połączenie LISTEN dla zmian listy: %s", exc)
            finally:
                self._ready.clear()
                self._close_all()
                if not connection.is_closed():
                    connection.terminate()
            if not self._closing:
                await asyncio.sleep(self._retry_delay)

    async def _listen(self, connection: asyncpg.Connection) -> None:
        lost = asyncio.Event()
        connection.add_termination_listener(lambda _: lost.set())
        await connection.add_listener(CHANNEL, self._on_notification)
        self._ready.set()
        logger.info("Nasłuch zmian listy aktywny")
        while not lost.is_set():
            try:
                await asyncio.wait_for(lost.wait(), self._health_check_seconds)
            except TimeoutError:
                # Martwe połączenie TCP nie zawsze daje znać samo — sprawdzamy je zapytaniem.
                await connection.execute("SELECT 1", timeout=5)

    def _on_notification(self, _connection, _pid: int, _channel: str, payload: str) -> None:
        try:
            event = json.loads(payload)
            household_id, user_id, kind = event["household"], event["user"], event["kind"]
        except (ValueError, KeyError, TypeError):
            logger.warning("Nieprawidłowe powiadomienie o zmianie listy: %r", payload)
            return
        for subscription in list(self._subscriptions.get(household_id, ())):
            if kind == "left":
                if subscription.user_id == user_id:
                    subscription._close()
                    self.unsubscribe(subscription)
            elif kind == "chat":
                subscription._signal("chat")
            elif user_id is None or subscription.user_id == user_id:
                subscription._signal("list")

    def _close_all(self) -> None:
        for subs in self._subscriptions.values():
            for subscription in subs:
                subscription._close()
        self._subscriptions.clear()

"""Wysyłka powiadomień push poza obsługą żądania HTTP (design D6).

Użycie w kolejnych zadaniach (#29–#31) — zawsze PO zapisaniu (commit) zmiany:

    notifier.send_to_household(
        household.id,
        Notification(NotificationType.SHOPPING_STARTED, "Zakupy", "ala idzie na zakupy"),
        exclude_user_ids={user.id},
    )
    notifier.send_to_users([shopper.user_id for shopper in shoppers], notification)

Obie metody planują zadanie `asyncio` i od razu wracają; wynik wysyłki trafia tylko do logów.
W handlerach `Notifier` daje zależność `kupto.deps.NotifierDep` (`request.app.state.notifier`).
"""

import asyncio
import logging
from collections.abc import Callable, Collection, Coroutine, Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from urllib.parse import urlsplit

import aiohttp
from pywebpush import WebPushException, webpush_async
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kupto.config import Settings
from kupto.db import utcnow
from kupto.models import PushSubscription, User
from kupto.push.notification import Notification, NotificationType
from kupto.push.vapid import VapidConfig

logger = logging.getLogger(__name__)

SEND_TIMEOUT_SECONDS = 10.0
MAX_CONCURRENT_SENDS = 10
SHUTDOWN_TIMEOUT_SECONDS = 5.0
# Usługa push: subskrypcja nie istnieje albo wygasła — usuwamy ją (RFC 8030, 6.2 / 7.3).
GONE_STATUSES = frozenset({404, 410})


@dataclass(frozen=True)
class Target:
    """Jedno urządzenie, na które idzie powiadomienie."""

    subscription_id: int
    endpoint: str
    p256dh: str
    auth: str


class PushTransport(Protocol):
    """Wysyła zaszyfrowane powiadomienie do usługi push i zwraca kod HTTP jej odpowiedzi."""

    async def send(
        self, target: Target, payload: str, *, ttl: int, urgency: str, topic: str | None
    ) -> int: ...

    async def aclose(self) -> None: ...


class WebPushTransport:
    """Transport produkcyjny: `pywebpush.webpush_async` na wspólnej sesji `aiohttp`."""

    def __init__(self, vapid: VapidConfig, timeout_seconds: float = SEND_TIMEOUT_SECONDS):
        self._vapid = vapid
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._session: aiohttp.ClientSession | None = None

    async def send(
        self, target: Target, payload: str, *, ttl: int, urgency: str, topic: str | None
    ) -> int:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        headers = {"Urgency": urgency} | ({"Topic": topic} if topic else {})
        try:
            response = await webpush_async(
                subscription_info={
                    "endpoint": target.endpoint,
                    "keys": {"p256dh": target.p256dh, "auth": target.auth},
                },
                data=payload,
                vapid_private_key=self._vapid.signer,
                # Nowy słownik przy każdym wywołaniu — pywebpush dopisuje do niego `aud` i `exp`.
                vapid_claims={"sub": self._vapid.subject},
                ttl=ttl,
                headers=headers,
                timeout=self._timeout,  # type: ignore[arg-type]  # aiohttp przyjmuje ClientTimeout
                aiohttp_session=self._session,
            )
        except WebPushException as exc:
            if exc.response is None:
                raise
            return exc.response.status
        return response.status  # type: ignore[union-attr]  # bez curl=True zawsze odpowiedź

    async def aclose(self) -> None:
        if self._session is not None:
            await self._session.close()


async def allowed_recipients(
    session: AsyncSession, user_ids: Collection[int], notification_type: NotificationType
) -> set[int]:
    """Adresaci, którzy chcą dostać powiadomienie danego typu.

    Punkt zaczepienia dla ustawień powiadomień (#32) — dziś przepuszcza wszystkich.
    """
    return set(user_ids)


class Notifier:
    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        transport: PushTransport | None = None,
        public_key: str | None = None,
    ):
        self._sessionmaker = sessionmaker
        self._transport = transport if public_key else None
        self.public_key = public_key if transport else None
        self._tasks: set[asyncio.Task[None]] = set()

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        sessionmaker: async_sessionmaker[AsyncSession],
        transport: PushTransport | None = None,
    ) -> "Notifier":
        """Bez poprawnych kluczy VAPID powiadomienia są wyłączone (`transport` jest pomijany)."""
        vapid = VapidConfig.from_settings(settings)
        if vapid is None:
            return cls(sessionmaker)
        return cls(sessionmaker, transport or WebPushTransport(vapid), vapid.public_key)

    @property
    def enabled(self) -> bool:
        return self._transport is not None

    # --- API dla funkcji aplikacji ---

    def send_to_users(self, user_ids: Iterable[int], notification: Notification) -> None:
        """Planuje wysyłkę na wszystkie urządzenia podanych użytkowników i od razu wraca."""
        ids = set(user_ids)
        if ids:
            self._schedule(notification, lambda: self.deliver_to_users(ids, notification))

    def send_to_household(
        self,
        household_id: int,
        notification: Notification,
        *,
        exclude_user_ids: Iterable[int] = (),
    ) -> None:
        """Planuje wysyłkę do członków gospodarstwa (z chwili wysyłki) z pominięciem wskazanych."""
        excluded = set(exclude_user_ids)
        self._schedule(
            notification,
            lambda: self.deliver_to_household(household_id, notification, excluded),
        )

    async def drain(self) -> None:
        """Czeka na wszystkie zaplanowane wysyłki (testy, wyłączanie aplikacji)."""
        while self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    async def aclose(self) -> None:
        try:
            await asyncio.wait_for(self.drain(), SHUTDOWN_TIMEOUT_SECONDS)
        except TimeoutError:
            logger.warning("Nie wszystkie powiadomienia push zostały wysłane przed zamknięciem.")
        if self._transport is not None:
            await self._transport.aclose()

    # --- Wysyłka (zadania w tle; testy mogą też czekać na nie bezpośrednio) ---

    async def deliver_to_household(
        self, household_id: int, notification: Notification, exclude_user_ids: Collection[int] = ()
    ) -> None:
        async with self._sessionmaker() as session:
            members = await session.scalars(
                select(User.id).where(
                    User.household_id == household_id, User.id.not_in(exclude_user_ids)
                )
            )
            user_ids = set(members)
        await self.deliver_to_users(user_ids, notification)

    async def deliver_to_users(self, user_ids: Collection[int], notification: Notification) -> None:
        if self._transport is None or not user_ids:
            return
        started_at = utcnow()
        async with self._sessionmaker() as session:
            recipients = await allowed_recipients(session, user_ids, notification.type)
            rows = await session.execute(
                select(
                    PushSubscription.id,
                    PushSubscription.endpoint,
                    PushSubscription.p256dh,
                    PushSubscription.auth,
                ).where(PushSubscription.user_id.in_(recipients))
            )
            targets = [Target(*row) for row in rows]
        if not targets:
            return

        payload = notification.payload()
        limit = asyncio.Semaphore(MAX_CONCURRENT_SENDS)

        async def send(target: Target) -> int | None:
            async with limit:
                return await self._send_one(target, payload, notification)

        statuses = await asyncio.gather(*(send(target) for target in targets))
        gone = [
            t.subscription_id for t, s in zip(targets, statuses, strict=True) if s in GONE_STATUSES
        ]
        if gone:
            await self._remove_gone(gone, started_at)

    async def _send_one(
        self, target: Target, payload: str, notification: Notification
    ) -> int | None:
        assert self._transport is not None
        host = urlsplit(target.endpoint).hostname  # bez pełnego adresu — to uprawnienie do wysyłki
        try:
            status = await self._transport.send(
                target,
                payload,
                ttl=notification.ttl,
                urgency=notification.urgency,
                topic=notification.topic,
            )
        except TimeoutError:
            logger.warning("Push %s do %s: przekroczony limit czasu.", notification.type, host)
            return None
        except Exception as exc:
            logger.warning(
                "Push %s do %s: błąd wysyłki (%s).", notification.type, host, type(exc).__name__
            )
            return None
        if status in GONE_STATUSES:
            logger.info(
                "Push %s do %s: subskrypcja wygasła (%s), usuwam.", notification.type, host, status
            )
        elif not 200 <= status < 300:
            logger.warning("Push %s do %s: odpowiedź %s.", notification.type, host, status)
        return status

    async def _remove_gone(self, subscription_ids: list[int], started_at: datetime) -> None:
        # Pomijamy subskrypcje zapisane ponownie w trakcie wysyłki (np. odnowione przez klienta).
        async with self._sessionmaker() as session:
            await session.execute(
                delete(PushSubscription).where(
                    PushSubscription.id.in_(subscription_ids),
                    PushSubscription.updated_at <= started_at,
                )
            )
            await session.commit()

    def _schedule(
        self, notification: Notification, job: Callable[[], Coroutine[Any, Any, None]]
    ) -> None:
        if self._transport is None:
            logger.info("Powiadomienia push wyłączone — pomijam %s.", notification.type)
            return
        task = asyncio.get_running_loop().create_task(self._guarded(notification, job()))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    @staticmethod
    async def _guarded(notification: Notification, job: Coroutine[Any, Any, None]) -> None:
        try:
            await job
        except Exception:
            logger.exception("Wysyłka powiadomienia %s nie powiodła się.", notification.type)

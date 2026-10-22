"""Ustawienia typów powiadomień per użytkownik (#32, design D2, D3).

W bazie są tylko jawne wybory użytkownika; brak wiersza oznacza wartość domyślną typu.
Nowy typ powiadomienia (np. przypomnienia #40) to wartość w `NotificationType` i wpis
w `DEFAULT_ENABLED` — bez migracji, także gdy ma być domyślnie wyłączony.
"""

from collections.abc import Collection

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from kupto.db import utcnow
from kupto.models import NotificationPreference, User
from kupto.push.notification import NotificationType

DEFAULT_ENABLED: dict[NotificationType, bool] = {
    NotificationType.SHOPPING_STARTED: True,
    NotificationType.ITEMS_ADDED: True,
    NotificationType.SHOPPING_FINISHED: True,
}


def default_enabled(notification_type: NotificationType) -> bool:
    return DEFAULT_ENABLED.get(notification_type, True)


async def preferences(session: AsyncSession, user: User) -> dict[NotificationType, bool]:
    """Wszystkie znane typy (w kolejności `NotificationType`) z wyborem użytkownika."""
    rows = await session.execute(
        select(NotificationPreference.type, NotificationPreference.enabled).where(
            NotificationPreference.user_id == user.id
        )
    )
    # Wiersze z typami, których kod już nie zna, są pomijane.
    chosen = {value: enabled for value, enabled in rows}
    return {t: chosen.get(t.value, default_enabled(t)) for t in NotificationType}


async def set_enabled(
    session: AsyncSession, user: User, notification_type: NotificationType, enabled: bool
) -> None:
    now = utcnow()
    await session.execute(
        insert(NotificationPreference)
        .values(user_id=user.id, type=notification_type.value, enabled=enabled, updated_at=now)
        .on_conflict_do_update(
            index_elements=[NotificationPreference.user_id, NotificationPreference.type],
            set_={"enabled": enabled, "updated_at": now},
        )
    )
    await session.commit()


async def recipients_wanting(
    session: AsyncSession, user_ids: Collection[int], notification_type: NotificationType
) -> set[int]:
    """Ci spośród `user_ids`, którzy chcą dostać powiadomienie danego typu."""
    if not user_ids:
        return set()
    rows = await session.execute(
        select(NotificationPreference.user_id, NotificationPreference.enabled).where(
            NotificationPreference.user_id.in_(user_ids),
            NotificationPreference.type == notification_type.value,
        )
    )
    chosen = {user_id: enabled for user_id, enabled in rows}
    default = default_enabled(notification_type)
    return {user_id for user_id in user_ids if chosen.get(user_id, default)}

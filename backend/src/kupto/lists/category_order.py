"""Kolejność kategorii użytkownika: ręczne przypięcia na tle kolejności automatycznej.

Kolejność jest osobna dla każdego użytkownika (nie dla gospodarstwa). Przypięcie zapamiętuje
miejsce w pełnej kolejności wszystkich kategorii, a nieprzypięte kategorie wypełniają pozostałe
miejsca w kolejności automatycznej (design D1).
"""

from dataclasses import dataclass

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from kupto.errors import DomainError
from kupto.lists import events
from kupto.lists.ordering import arrange
from kupto.models import Category, User, UserCategoryPin


@dataclass(frozen=True)
class CategoryOrder:
    categories: list[Category]
    pinned: frozenset[Category]


def automatic_order() -> list[Category]:
    """Kolejność bazowa, wokół której układają się przypięcia; w #38 — kolejność wyuczona."""
    return list(Category)


AUTOMATIC = CategoryOrder(categories=automatic_order(), pinned=frozenset())


async def get_order(session: AsyncSession, user: User) -> CategoryOrder:
    pins = await _pins(session, user)
    return CategoryOrder(categories=arrange(automatic_order(), pins), pinned=frozenset(pins))


async def pin(
    session: AsyncSession,
    user: User,
    category: Category,
    after: Category | None,
    before: Category | None,
) -> None:
    """Przenosi kategorię między sąsiadów z widoku klienta i przypina ją na nowym miejscu.

    Brak `after` oznacza początek, brak `before` — koniec pełnej kolejności (design D2).
    """
    if category in (after, before):
        raise DomainError("Kategorii nie można przenieść względem niej samej.")
    # Blokada użytkownika: równoległe przeniesienia (np. z dwóch telefonów) idą po kolei.
    await session.execute(select(User.id).where(User.id == user.id).with_for_update())
    pins = await _pins(session, user)
    order = arrange(automatic_order(), pins)
    order.remove(category)
    if after is None:
        index = 0
    elif before is None:
        index = len(order)
    else:
        index = order.index(after) + 1
    order.insert(index, category)
    # Wcześniejsze przypięcia dostają swoje nowe miejsca, więc zachowują względny układ.
    pinned = set(pins) | {category}
    await session.execute(delete(UserCategoryPin).where(UserCategoryPin.user_id == user.id))
    await session.execute(
        insert(UserCategoryPin),
        [
            {"user_id": user.id, "category": c, "position": position}
            for position, c in enumerate(order)
            if c in pinned
        ],
    )
    await events.order_changed(session, user)
    await session.commit()


async def unpin(session: AsyncSession, user: User, category: Category) -> None:
    await session.execute(
        delete(UserCategoryPin).where(
            UserCategoryPin.user_id == user.id, UserCategoryPin.category == category
        )
    )
    await events.order_changed(session, user)
    await session.commit()


async def reset(session: AsyncSession, user: User) -> None:
    await session.execute(delete(UserCategoryPin).where(UserCategoryPin.user_id == user.id))
    await events.order_changed(session, user)
    await session.commit()


async def _pins(session: AsyncSession, user: User) -> dict[Category, int]:
    rows = await session.execute(
        select(UserCategoryPin.category, UserCategoryPin.position).where(
            UserCategoryPin.user_id == user.id
        )
    )
    return {category: position for category, position in rows}

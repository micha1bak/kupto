"""Reguły wspólnej listy zakupów — jedyne miejsce, w którym zmienia się jej stan.

Korzystają z nich zarówno endpointy REST, jak i narzędzia asystenta czatu.
Każda operacja jest ograniczona do listy gospodarstwa wywołującego i kończy się commitem.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from kupto.db import utcnow
from kupto.errors import Forbidden, NotFound
from kupto.lists.quantities import clean_name, normalize_name
from kupto.models import (
    Category,
    Household,
    HouseholdProduct,
    ListItem,
    Need,
    ShoppingList,
    Unit,
    User,
)


@dataclass(frozen=True)
class NeedInput:
    name: str
    amount: Decimal | None = None
    unit: Unit | None = None
    note: str | None = None
    category: Category | None = None


@dataclass(frozen=True)
class AddedNeed:
    item_name: str
    category: Category
    merged: bool  # True, jeśli produkt był już na liście


async def get_list(session: AsyncSession, household: Household) -> ShoppingList:
    shopping_list = await session.scalar(
        select(ShoppingList)
        .where(ShoppingList.household_id == household.id)
        .options(
            selectinload(ShoppingList.items).selectinload(ListItem.needs).selectinload(Need.user),
            selectinload(ShoppingList.items).selectinload(ListItem.bought_by),
        )
        .execution_options(populate_existing=True)
    )
    assert shopping_list is not None
    return shopping_list


async def add_needs(
    session: AsyncSession, household: Household, user: User, inputs: Sequence[NeedInput]
) -> list[AddedNeed]:
    list_id = await _list_id(session, household)
    added: list[AddedNeed] = []
    for need_input in inputs:
        normalized = normalize_name(need_input.name)
        if need_input.category is not None:
            await _remember_category(session, household, normalized, need_input.category)
        item = await _find_item(session, list_id, normalized)
        created = False
        if item is None:
            category = need_input.category or await _known_category(session, household, normalized)
            item, created = await _insert_item_if_absent(
                session, list_id, clean_name(need_input.name), normalized, category
            )
        if not created:
            if item.category == Category.OTHER and need_input.category is not None:
                item.category = need_input.category
            # Nowe zapotrzebowanie na kupiony już produkt oznacza, że znów trzeba go kupić.
            item.bought_at = None
            item.bought_by_id = None
        session.add(
            Need(
                item_id=item.id,
                user_id=user.id,
                amount=need_input.amount,
                unit=need_input.unit,
                note=need_input.note,
            )
        )
        added.append(AddedNeed(item_name=item.name, category=item.category, merged=not created))
    await session.commit()
    return added


async def update_need(
    session: AsyncSession,
    household: Household,
    user: User,
    need_id: int,
    changes: dict[str, object],
) -> None:
    need = await _own_need(session, household, user, need_id)
    for field in ("amount", "unit", "note"):
        if field in changes:
            setattr(need, field, changes[field])
    await session.commit()


async def withdraw_need(
    session: AsyncSession, household: Household, user: User, need_id: int
) -> None:
    need = await _own_need(session, household, user, need_id)
    item_id = need.item_id
    await session.delete(need)
    await session.flush()
    remaining = await session.scalar(select(Need.id).where(Need.item_id == item_id).limit(1))
    if remaining is None:
        await session.execute(delete(ListItem).where(ListItem.id == item_id))
    await session.commit()


async def remove_item(session: AsyncSession, household: Household, item_id: int) -> str:
    item = await _get_item(session, household, item_id)
    name = item.name
    await session.delete(item)
    await session.commit()
    return name


async def set_bought(
    session: AsyncSession,
    household: Household,
    user: User,
    item_ids: Sequence[int],
    bought: bool,
) -> list[str]:
    found = await session.scalars(
        select(ListItem)
        .join(ShoppingList)
        .where(ListItem.id.in_(item_ids), ShoppingList.household_id == household.id)
    )
    by_id = {item.id: item for item in found}
    if len(by_id) != len(set(item_ids)):
        raise NotFound("Nie ma takiej pozycji na liście.")
    items = [by_id[item_id] for item_id in dict.fromkeys(item_ids)]
    now = utcnow()
    for item in items:
        item.bought_at = now if bought else None
        item.bought_by_id = user.id if bought else None
    await session.commit()
    return [item.name for item in items]


async def finish_shopping(session: AsyncSession, household: Household) -> int:
    list_id = await _list_id(session, household)
    result = await session.execute(
        delete(ListItem).where(ListItem.list_id == list_id, ListItem.bought_at.is_not(None))
    )
    await session.commit()
    return result.rowcount


async def _find_item(session: AsyncSession, list_id: int, normalized: str) -> ListItem | None:
    return await session.scalar(
        select(ListItem)
        .where(ListItem.list_id == list_id, ListItem.normalized_name == normalized)
        .execution_options(populate_existing=True)
    )


async def _insert_item_if_absent(
    session: AsyncSession, list_id: int, name: str, normalized: str, category: Category
) -> tuple[ListItem, bool]:
    """Wstawia pozycję albo — gdy ktoś równolegle dodał ten sam produkt — zwraca istniejącą.

    ON CONFLICT DO NOTHING zamiast zwykłego INSERT: dwa jednoczesne zgłoszenia nowego produktu
    mają się scalić, a nie skończyć błędem unikalności.
    """
    inserted_id = await session.scalar(
        insert(ListItem)
        .values(
            list_id=list_id,
            name=name,
            normalized_name=normalized,
            category=category,
            created_at=utcnow(),
        )
        .on_conflict_do_nothing(index_elements=["list_id", "normalized_name"])
        .returning(ListItem.id)
    )
    item = await _find_item(session, list_id, normalized)
    assert item is not None
    return item, inserted_id is not None


async def _list_id(session: AsyncSession, household: Household) -> int:
    list_id = await session.scalar(
        select(ShoppingList.id).where(ShoppingList.household_id == household.id)
    )
    assert list_id is not None
    return list_id


async def _get_item(session: AsyncSession, household: Household, item_id: int) -> ListItem:
    item = await session.scalar(
        select(ListItem)
        .join(ShoppingList)
        .where(ListItem.id == item_id, ShoppingList.household_id == household.id)
    )
    if item is None:
        raise NotFound("Nie ma takiej pozycji na liście.")
    return item


async def _own_need(session: AsyncSession, household: Household, user: User, need_id: int) -> Need:
    need = await session.scalar(
        select(Need)
        .join(ListItem)
        .join(ShoppingList)
        .where(Need.id == need_id, ShoppingList.household_id == household.id)
    )
    if need is None:
        raise NotFound("Nie ma takiego zapotrzebowania na liście.")
    if need.user_id != user.id:
        raise Forbidden("Możesz zmieniać tylko własne zapotrzebowania.")
    return need


async def _known_category(session: AsyncSession, household: Household, normalized: str) -> Category:
    category = await session.scalar(
        select(HouseholdProduct.category).where(
            HouseholdProduct.household_id == household.id,
            HouseholdProduct.normalized_name == normalized,
        )
    )
    return category or Category.OTHER


async def _remember_category(
    session: AsyncSession, household: Household, normalized: str, category: Category
) -> None:
    statement = insert(HouseholdProduct).values(
        household_id=household.id, normalized_name=normalized, category=category
    )
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=["household_id", "normalized_name"],
            set_={"category": statement.excluded.category},
        )
    )

"""Kolejność produktów użytkownika w obrębie kategorii: przypięcia na tle kolejności bazowej.

Kolejność jest osobna dla każdego użytkownika i zapamiętana per produkt (znormalizowana
nazwa), więc działa także przy kolejnym dodaniu produktu na listę. Przypięcie to kotwica
(nieprzypięty produkt, za którym stoi przypięty, albo początek / koniec kategorii) i ranga
wśród przypięć kategorii — zmiana product-order, design D2–D3.
"""

from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass, field

from sqlalchemy import delete, insert, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from kupto.errors import Conflict, DomainError, NotFound
from kupto.lists import events
from kupto.lists.ordering import Anchor, arrange_anchored
from kupto.models import Category, Household, ListItem, ShoppingList, User, UserProductPin

type Pins = Mapping[str, Anchor[str]]


def product_base_order(category: Category, names: Iterable[str]) -> list[str]:
    """Kolejność bazowa produktów kategorii, wokół której układają się przypięcia.

    Dziś alfabetycznie po znormalizowanej nazwie; w #38 — kolejność wyuczona z historii
    zakupów (dla zbioru `names`, w którym są też produkty chwilowo nieobecne na liście).
    """
    return sorted(names)


def full_order(category: Category, present: Collection[str], pins: Pins) -> list[str]:
    """Pełna kolejność kategorii: produkty obecne, przypięte i kotwice przypięć (design D2).

    Nieobecne produkty wyznaczają tylko względny układ — wywołujący je odfiltrowuje.
    """
    universe = {*present, *pins, *(a.after for a in pins.values() if a.after is not None)}
    return arrange_anchored(product_base_order(category, universe), pins)


@dataclass(frozen=True)
class ProductOrder:
    """Przypięcia produktów jednego użytkownika, pogrupowane według kategorii."""

    pins: Mapping[Category, Pins] = field(default_factory=dict)

    def arrange(self, category: Category, items: Iterable[ListItem]) -> list[ListItem]:
        by_name = {item.normalized_name: item for item in items}
        order = full_order(category, by_name.keys(), self.pins.get(category, {}))
        return [by_name[name] for name in order if name in by_name]

    def is_pinned(self, item: ListItem) -> bool:
        return item.normalized_name in self.pins.get(item.category, {})


BASE = ProductOrder()


async def get_order(session: AsyncSession, user: User) -> ProductOrder:
    rows = await session.scalars(select(UserProductPin).where(UserProductPin.user_id == user.id))
    pins: dict[Category, dict[str, Anchor[str]]] = {}
    for pin in rows:
        pins.setdefault(pin.category, {})[pin.normalized_name] = _anchor(pin)
    return ProductOrder(pins)


async def pin(
    session: AsyncSession,
    household: Household,
    user: User,
    item_id: int,
    after_id: int | None,
    before_id: int | None,
) -> None:
    """Przenosi produkt pozycji między sąsiadów z widoku klienta i przypina go na nowym miejscu.

    Brak `after` oznacza początek kategorii, brak `before` (przy podanym `after`) — koniec.
    Sąsiad usunięty w międzyczasie z listy jest pomijany (design D3).
    """
    if item_id in (after_id, before_id):
        raise DomainError("Produktu nie można przenieść względem niego samego.")
    item = await _item(session, household, item_id)
    if item is None:
        raise NotFound("Nie ma takiej pozycji na liście.")
    after = await _neighbour(session, household, item, after_id)
    before = await _neighbour(session, household, item, before_id)
    category, name = item.category, item.normalized_name
    # Blokada użytkownika: równoległe przeniesienia (np. z dwóch telefonów) idą po kolei.
    await session.execute(select(User.id).where(User.id == user.id).with_for_update())
    pins = await _category_pins(session, user, category)
    present = await session.scalars(
        select(ListItem.normalized_name).where(
            ListItem.list_id == item.list_id, ListItem.category == category
        )
    )
    order = full_order(category, set(present), pins)
    order.remove(name)
    at_end = False
    if after_id is None:
        index = 0
    elif before_id is None:
        index, at_end = len(order), True
    elif after is not None:
        index = order.index(after) + 1
    elif before is not None:
        index = order.index(before)
    else:
        raise Conflict("Lista się zmieniła — odśwież ją i spróbuj ponownie.")
    order.insert(index, name)

    pinned = {*pins, name}
    ends = {n for n, anchor in pins.items() if anchor.at_end and n != name}
    if at_end:
        ends.add(name)
    # Kotwice wszystkich przypięć kategorii z nowej kolejności: zakotwiczone za przenoszonym
    # produktem przechodzą na jego dawne miejsce, a rangi zachowują względny układ (design D3).
    rows = []
    for position, element in enumerate(n for n in order if n in pinned):
        if element in ends:
            anchor = Anchor(rank=position, at_end=True)
        else:
            anchor = _anchor_before(order[: order.index(element)], pinned, ends, position)
        if anchor.at_end:
            ends.add(element)
        rows.append(
            {
                "user_id": user.id,
                "normalized_name": element,
                "category": category,
                "after_name": anchor.after,
                "at_end": anchor.at_end,
                "position": anchor.rank,
            }
        )
    await session.execute(
        delete(UserProductPin).where(
            UserProductPin.user_id == user.id,
            or_(UserProductPin.category == category, UserProductPin.normalized_name == name),
        )
    )
    await session.execute(insert(UserProductPin), rows)
    await events.order_changed(session, user)
    await session.commit()


async def unpin(session: AsyncSession, household: Household, user: User, item_id: int) -> None:
    item = await _item(session, household, item_id)
    if item is None:
        raise NotFound("Nie ma takiej pozycji na liście.")
    await session.execute(
        delete(UserProductPin).where(
            UserProductPin.user_id == user.id,
            UserProductPin.normalized_name == item.normalized_name,
        )
    )
    await events.order_changed(session, user)
    await session.commit()


def _anchor_before(
    preceding: list[str], pinned: set[str], ends: set[str], rank: int
) -> Anchor[str]:
    """Kotwica elementu z jego poprzedników: najbliższy nieprzypięty albo blok końcowy."""
    for element in reversed(preceding):
        if element not in pinned:
            return Anchor(rank=rank, after=element)
        if element in ends:
            return Anchor(rank=rank, at_end=True)
    return Anchor(rank=rank)


def _anchor(pin: UserProductPin) -> Anchor[str]:
    return Anchor(rank=pin.position, after=pin.after_name, at_end=pin.at_end)


async def _category_pins(
    session: AsyncSession, user: User, category: Category
) -> dict[str, Anchor[str]]:
    rows = await session.scalars(
        select(UserProductPin).where(
            UserProductPin.user_id == user.id, UserProductPin.category == category
        )
    )
    return {pin.normalized_name: _anchor(pin) for pin in rows}


async def _item(session: AsyncSession, household: Household, item_id: int) -> ListItem | None:
    return await session.scalar(
        select(ListItem)
        .join(ShoppingList)
        .where(ListItem.id == item_id, ShoppingList.household_id == household.id)
    )


async def _neighbour(
    session: AsyncSession, household: Household, item: ListItem, neighbour_id: int | None
) -> str | None:
    if neighbour_id is None:
        return None
    neighbour = await _item(session, household, neighbour_id)
    if neighbour is None:
        return None  # usunięty w międzyczasie albo spoza listy — jak nieaktualny widok
    if neighbour.category != item.category:
        raise DomainError("Produkt można przenieść tylko w obrębie jego kategorii.")
    return neighbour.normalized_name

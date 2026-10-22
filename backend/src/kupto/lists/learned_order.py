"""Kolejność wyuczona z historii odhaczeń — design D1–D3 zmiany learned-order.

Prosta, przewidywalna heurystyka na historii gospodarstwa:

1. Przejście = pozycje jednego zakończenia zakupów odhaczone przez jedną osobę, w kolejności
   odhaczania (`bought_at`, remis — `id`); liczą się przejścia z co najmniej `MIN_ITEMS`
   pozycjami.
2. Bierzemy `WINDOW` ostatnich przejść użytkownika; gdy jest ich mniej niż `MIN_PASSES` —
   ostatnie przejścia wszystkich członków gospodarstwa; gdy i tych za mało — brak nauki
   (kolejność bazowa jak dotąd).
3. Względne miejsce pozycji `i` w przejściu z `n` pozycjami to `i / (n − 1)`. Wynik produktu
   to mediana jego miejsc, a kategorii — mediana średnich miejsc jej pozycji w przejściach.
4. Wynik ma tylko element obecny w co najmniej `MIN_OBSERVATIONS` przejściach.

Liczymy w locie przy każdym odczycie (bez tabeli) — historia przybywa tylko przy zakończeniu
zakupów, więc kolejność nie zmienia się w trakcie zakupów (design D6–D7).
"""

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from statistics import fmean, median

from sqlalchemy import func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from kupto.models import Category, PurchasedItem, ShoppingTrip, User

WINDOW = 10
MIN_PASSES = 3
MIN_ITEMS = 2
MIN_OBSERVATIONS = 2

type Pass = Sequence[tuple[str, Category]]  # (znormalizowana nazwa, kategoria) w kolejności


@dataclass(frozen=True)
class LearnedOrder:
    """Wyniki (mniejszy = wcześniej w sklepie) dla elementów, których kolejność znamy."""

    categories: Mapping[Category, float] = field(default_factory=dict)
    products: Mapping[str, float] = field(default_factory=dict)  # po znormalizowanej nazwie


NOTHING = LearnedOrder()


def learn(passes: Iterable[Pass]) -> LearnedOrder:
    """Wyniki kategorii i produktów z przejść (każde z co najmniej dwiema pozycjami)."""
    categories: dict[Category, list[float]] = defaultdict(list)
    products: dict[str, list[float]] = defaultdict(list)
    for items in passes:
        last = len(items) - 1
        in_pass: dict[Category, list[float]] = defaultdict(list)
        for index, (name, category) in enumerate(items):
            place = index / last
            products[name].append(place)
            in_pass[category].append(place)
        for category, places in in_pass.items():
            categories[category].append(fmean(places))
    return LearnedOrder(categories=_scores(categories), products=_scores(products))


async def learned_order(session: AsyncSession, user: User) -> LearnedOrder:
    """Kolejność wyuczona użytkownika: z własnych przejść, przy zimnym starcie z gospodarstwa."""
    if user.household_id is None:
        return NOTHING
    passes = await _passes(session, user.household_id, user.id)
    if len(passes) < MIN_PASSES:
        passes = await _passes(session, user.household_id, None)
    if len(passes) < MIN_PASSES:
        return NOTHING
    return learn(passes)


def _scores[T](places: Mapping[T, list[float]]) -> dict[T, float]:
    return {
        element: median(observed)
        for element, observed in places.items()
        if len(observed) >= MIN_OBSERVATIONS
    }


async def _passes(session: AsyncSession, household_id: int, user_id: int | None) -> list[Pass]:
    """Ostatnie przejścia gospodarstwa — tylko użytkownika `user_id` albo wszystkich członków."""
    who = (
        PurchasedItem.bought_by_id == user_id
        if user_id is not None
        else PurchasedItem.bought_by_id.is_not(None)
    )
    recent = (
        select(PurchasedItem.trip_id, PurchasedItem.bought_by_id)
        .join(ShoppingTrip)
        .where(ShoppingTrip.household_id == household_id, who)
        .group_by(PurchasedItem.trip_id, PurchasedItem.bought_by_id, ShoppingTrip.finished_at)
        .having(func.count() >= MIN_ITEMS)
        .order_by(ShoppingTrip.finished_at.desc(), PurchasedItem.trip_id.desc())
        .limit(WINDOW)
    )
    rows = await session.execute(
        select(
            PurchasedItem.trip_id,
            PurchasedItem.bought_by_id,
            PurchasedItem.normalized_name,
            PurchasedItem.category,
        )
        .where(tuple_(PurchasedItem.trip_id, PurchasedItem.bought_by_id).in_(recent))
        .order_by(
            PurchasedItem.trip_id,
            PurchasedItem.bought_by_id,
            PurchasedItem.bought_at,
            PurchasedItem.id,
        )
    )
    passes: dict[tuple[int, int], list[tuple[str, Category]]] = defaultdict(list)
    for trip_id, bought_by_id, name, category in rows:
        passes[trip_id, bought_by_id].append((name, category))
    return list(passes.values())

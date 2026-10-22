"""„To co zwykle” — produkty kupowane regularnie, których nie ma teraz na liście.

Prosta, przewidywalna heurystyka na historii gospodarstwa (design D1 w change `usual-items`):

1. Pozycje historii z zakończeń zakupów z ostatnich `HISTORY_WINDOW`, grupowane po
   `normalized_name`; datą zakupu jest `finished_at` zakończenia.
2. Produkt jest regularny, gdy był kupiony w co najmniej `MIN_PURCHASES` zakończeniach.
3. Typowy odstęp = mediana odstępów między kolejnymi zakupami, nie mniej niż `MIN_INTERVAL`.
4. Zaległość = czas od ostatniego zakupu / typowy odstęp; podpowiadamy, gdy mieści się
   w [`MIN_OVERDUE`, `MAX_OVERDUE`] (powyżej — gospodarstwo raczej przestało to kupować).
5. Pomijamy produkty, które są teraz na liście (także odhaczone).
6. Typowa ilość: jednostka podawana w największej liczbie zakupów, ilość = mediana sum
   zapotrzebowań w tej jednostce.

Funkcja `usual_missing` tylko czyta i jest wspólna dla API, czatu i przypomnień push (#40).
"""

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from itertools import pairwise
from statistics import median

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from kupto.db import utcnow
from kupto.lists.quantities import aggregate_quantities
from kupto.models import (
    Category,
    Household,
    ListItem,
    PurchasedItem,
    ShoppingList,
    ShoppingTrip,
    Unit,
)

HISTORY_WINDOW = timedelta(days=365)
MIN_PURCHASES = 3
MIN_INTERVAL = timedelta(days=1)
MIN_OVERDUE = 0.8
MAX_OVERDUE = 3.0
MAX_SUGGESTIONS = 20  # w odpowiedzi API


@dataclass(frozen=True)
class Suggestion:
    name: str  # z ostatniego zakupu
    normalized_name: str
    category: Category  # z ostatniego zakupu
    amount: Decimal | None  # typowa ilość; None — w historii nie podawano ilości
    unit: Unit | None
    times_bought: int  # liczba zakończeń zakupów z produktem w oknie historii
    typical_interval: timedelta
    last_bought_at: datetime  # `finished_at` ostatniego zakończenia z produktem
    since_last: timedelta
    overdue: float  # since_last / typical_interval


async def usual_missing(
    session: AsyncSession, household: Household, now: datetime | None = None
) -> list[Suggestion]:
    """Zwykłe produkty gospodarstwa, których brakuje na liście; największa zaległość pierwsza."""
    now = now or utcnow()
    rows = await session.execute(
        select(PurchasedItem, ShoppingTrip.finished_at)
        .join(ShoppingTrip)
        .where(
            ShoppingTrip.household_id == household.id,
            ShoppingTrip.finished_at >= now - HISTORY_WINDOW,
            ShoppingTrip.finished_at <= now,
        )
        .order_by(ShoppingTrip.finished_at, PurchasedItem.id)
        .options(selectinload(PurchasedItem.needs))
    )
    # normalized_name → zakupy (finished_at, pozycja) rosnąco w czasie, po jednym na zakończenie
    purchases: dict[str, dict[int, tuple[datetime, PurchasedItem]]] = defaultdict(dict)
    for item, finished_at in rows.all():
        purchases[item.normalized_name].setdefault(item.trip_id, (finished_at, item))

    on_list = set(
        await session.scalars(
            select(ListItem.normalized_name)
            .join(ShoppingList)
            .where(ShoppingList.household_id == household.id)
        )
    )

    suggestions = []
    for normalized, by_trip in purchases.items():
        if normalized in on_list or len(by_trip) < MIN_PURCHASES:
            continue
        history = sorted(by_trip.values(), key=lambda p: p[0])
        dates = [finished_at for finished_at, _ in history]
        typical = max(median(b - a for a, b in pairwise(dates)), MIN_INTERVAL)
        since_last = now - dates[-1]
        overdue = since_last / typical
        if not MIN_OVERDUE <= overdue <= MAX_OVERDUE:
            continue
        last = history[-1][1]
        amount, unit = _typical_quantity([item for _, item in history])
        suggestions.append(
            Suggestion(
                name=last.name,
                normalized_name=normalized,
                category=last.category,
                amount=amount,
                unit=unit,
                times_bought=len(history),
                typical_interval=typical,
                last_bought_at=dates[-1],
                since_last=since_last,
                overdue=overdue,
            )
        )
    suggestions.sort(key=lambda s: (-s.overdue, -s.times_bought, s.normalized_name))
    return suggestions


def _typical_quantity(history: list[PurchasedItem]) -> tuple[Decimal | None, Unit | None]:
    """Jednostka najczęściej podawana w zakupach (remis — nowsza) i mediana ilości w niej."""
    per_purchase = [
        {q.unit: q.amount for q in aggregate_quantities((n.amount, n.unit) for n in item.needs)}
        for item in history
    ]
    counts = Counter(unit for totals in per_purchase for unit in totals)
    if not counts:
        return None, None
    last_seen = {unit: i for i, totals in enumerate(per_purchase) for unit in totals}
    unit = max(counts, key=lambda u: (counts[u], last_seen[u]))
    amount = median(totals[unit] for totals in per_purchase if unit in totals)
    # Jak w sumach ilości na liście: 2.000 → 2, 0.500 → 0.5 (bez notacji wykładniczej).
    (typical,) = aggregate_quantities([(Decimal(amount), unit)])
    return typical.amount, unit

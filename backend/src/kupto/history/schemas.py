from datetime import datetime, timedelta

from pydantic import BaseModel

from kupto.history.usual import Suggestion
from kupto.lists.category_order import CategoryOrder
from kupto.lists.quantities import aggregate_quantities
from kupto.lists.schemas import QuantityOut
from kupto.models import Category, PurchasedItem, PurchasedNeed, ShoppingTrip, Unit


class PurchasedNeedOut(BaseModel):
    user_id: int | None
    login: str | None
    amount: float | None
    unit: Unit | None
    note: str | None
    requested_at: datetime


class PurchasedItemOut(BaseModel):
    id: int
    name: str
    category: Category
    quantities: list[QuantityOut]
    needs: list[PurchasedNeedOut]
    bought_at: datetime
    bought_by: str | None


class PurchasedGroup(BaseModel):
    category: Category
    items: list[PurchasedItemOut]


class TripOut(BaseModel):
    id: int
    finished_at: datetime
    finished_by: str | None
    item_count: int
    # Kategorie w kolejności zalogowanego użytkownika (jak na liście); w grupie alfabetycznie.
    groups: list[PurchasedGroup]


class TripPageOut(BaseModel):
    trips: list[TripOut]
    # Wartość `before` dla następnej (starszej) strony; NULL — to już wszystkie zakończenia.
    next_cursor: int | None


class ProductOut(BaseModel):
    name: str
    category: Category
    last_bought_at: datetime
    last_bought_by: str | None
    last_trip_id: int
    last_quantities: list[QuantityOut]
    times_bought: int


def _quantities(needs: list[PurchasedNeed]) -> list[QuantityOut]:
    return [
        QuantityOut(amount=float(q.amount), unit=q.unit)
        for q in aggregate_quantities((n.amount, n.unit) for n in needs)
    ]


def purchased_item_out(item: PurchasedItem, logins: dict[int, str]) -> PurchasedItemOut:
    return PurchasedItemOut(
        id=item.id,
        name=item.name,
        category=item.category,
        quantities=_quantities(item.needs),
        needs=[
            PurchasedNeedOut(
                user_id=n.user_id,
                login=logins.get(n.user_id) if n.user_id is not None else None,
                amount=float(n.amount) if n.amount is not None else None,
                unit=n.unit,
                note=n.note,
                requested_at=n.requested_at,
            )
            for n in item.needs
        ],
        bought_at=item.bought_at,
        bought_by=logins.get(item.bought_by_id) if item.bought_by_id is not None else None,
    )


def trip_out(trip: ShoppingTrip, order: CategoryOrder, logins: dict[int, str]) -> TripOut:
    groups = []
    for category in order.categories:
        items = sorted(
            (i for i in trip.items if i.category == category), key=lambda i: i.normalized_name
        )
        if items:
            groups.append(
                PurchasedGroup(
                    category=category, items=[purchased_item_out(i, logins) for i in items]
                )
            )
    return TripOut(
        id=trip.id,
        finished_at=trip.finished_at,
        finished_by=logins.get(trip.finished_by_id) if trip.finished_by_id is not None else None,
        item_count=len(trip.items),
        groups=groups,
    )


def product_out(item: PurchasedItem, times_bought: int, logins: dict[int, str]) -> ProductOut:
    return ProductOut(
        name=item.name,
        category=item.category,
        last_bought_at=item.bought_at,
        last_bought_by=logins.get(item.bought_by_id) if item.bought_by_id is not None else None,
        last_trip_id=item.trip_id,
        last_quantities=_quantities(item.needs),
        times_bought=times_bought,
    )


class UsualOut(BaseModel):
    """Produkt kupowany zwykle, którego brakuje na liście (`kupto.history.usual`)."""

    name: str
    category: Category
    amount: float | None  # typowa ilość; NULL — w historii nie podawano ilości
    unit: Unit | None
    times_bought: int
    typical_interval_days: float
    last_bought_at: datetime
    overdue: float  # czas od ostatniego zakupu / typowy odstęp


def usual_out(suggestion: Suggestion) -> UsualOut:
    return UsualOut(
        name=suggestion.name,
        category=suggestion.category,
        amount=float(suggestion.amount) if suggestion.amount is not None else None,
        unit=suggestion.unit,
        times_bought=suggestion.times_bought,
        typical_interval_days=round(suggestion.typical_interval / timedelta(days=1), 1),
        last_bought_at=suggestion.last_bought_at,
        overdue=round(suggestion.overdue, 2),
    )

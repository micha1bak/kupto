"""Odczyt historii zakupów gospodarstwa — tylko do odczytu.

Historię zapisuje `kupto.lists.service.finish_shopping`; tu ją przeglądamy i przeszukujemy.
Każde zapytanie jest ograniczone do zakończeń zakupów gospodarstwa wywołującego.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from kupto.errors import DomainError, NotFound
from kupto.lists.quantities import normalize_name
from kupto.models import Household, PurchasedItem, ShoppingTrip, User

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 50
MAX_SEARCH_RESULTS = 20

# Porównanie bez polskich znaków bez rozszerzenia `unaccent` (wymagałoby migracji) — design D4.
_POLISH = "ąćęłńóśźż"
_ASCII = "acelnoszz"
_FOLD = str.maketrans(_POLISH, _ASCII)


class InvalidSearch(DomainError):
    status_code = 422


@dataclass(frozen=True)
class TripPage:
    trips: list[ShoppingTrip]
    next_cursor: int | None  # id ostatniego zakończenia na stronie, gdy są starsze


@dataclass(frozen=True)
class ProductMatch:
    last: PurchasedItem  # ostatni zakup produktu (z zapotrzebowaniami)
    times_bought: int


def fold(text: str) -> str:
    """Postać nazwy do wyszukiwania: znormalizowana, małe litery, bez polskich znaków."""
    return normalize_name(text).translate(_FOLD)


async def list_trips(
    session: AsyncSession,
    household: Household,
    before: int | None = None,
    limit: int = DEFAULT_PAGE_SIZE,
) -> TripPage:
    """Zakończenia zakupów od najnowszych; `before` to kursor z poprzedniej strony (design D2)."""
    statement = (
        select(ShoppingTrip)
        .where(ShoppingTrip.household_id == household.id)
        .order_by(ShoppingTrip.finished_at.desc(), ShoppingTrip.id.desc())
        .limit(limit + 1)
        .options(selectinload(ShoppingTrip.items).selectinload(PurchasedItem.needs))
    )
    if before is not None:
        cursor_finished_at = await session.scalar(
            select(ShoppingTrip.finished_at).where(
                ShoppingTrip.id == before, ShoppingTrip.household_id == household.id
            )
        )
        if cursor_finished_at is None:
            raise NotFound("Nie ma takiego zakończenia zakupów w historii.")
        statement = statement.where(
            tuple_(ShoppingTrip.finished_at, ShoppingTrip.id) < tuple_(cursor_finished_at, before)
        )
    trips = list(await session.scalars(statement))
    has_more = len(trips) > limit
    trips = trips[:limit]
    return TripPage(trips=trips, next_cursor=trips[-1].id if has_more else None)


async def search_products(
    session: AsyncSession, household: Household, query: str
) -> list[ProductMatch]:
    """Produkty z historii pasujące do frazy: ostatni zakup i liczba zakupów, najświeższe pierwsze.

    Dopasowanie po fragmencie nazwy bez względu na wielkość liter i polskie znaki (design D4).
    """
    phrase = fold(query)
    if not phrase:
        raise InvalidSearch("Wpisz nazwę produktu.")
    pattern = "%" + phrase.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    folded_name = func.translate(func.lower(PurchasedItem.normalized_name), _POLISH, _ASCII)
    ranked = (
        select(
            PurchasedItem.id,
            func.row_number()
            .over(
                partition_by=PurchasedItem.normalized_name,
                order_by=(PurchasedItem.bought_at.desc(), PurchasedItem.id.desc()),
            )
            .label("rank"),
            func.count().over(partition_by=PurchasedItem.normalized_name).label("times_bought"),
        )
        .join(ShoppingTrip)
        .where(
            ShoppingTrip.household_id == household.id,
            folded_name.like(pattern, escape="\\"),
        )
        .subquery()
    )
    rows = await session.execute(
        select(PurchasedItem, ranked.c.times_bought)
        .join(ranked, PurchasedItem.id == ranked.c.id)
        .where(ranked.c.rank == 1)
        .order_by(PurchasedItem.bought_at.desc(), PurchasedItem.id.desc())
        .limit(MAX_SEARCH_RESULTS)
        .options(selectinload(PurchasedItem.needs))
    )
    return [ProductMatch(last=item, times_bought=times) for item, times in rows.all()]


async def logins(session: AsyncSession, user_ids: Iterable[int | None]) -> dict[int, str]:
    """Loginy autorów wpisów historii; usunięte konta (NULL) po prostu nie mają loginu."""
    ids = {user_id for user_id in user_ids if user_id is not None}
    if not ids:
        return {}
    rows = await session.execute(select(User.id, User.login).where(User.id.in_(ids)))
    return dict(rows.all())

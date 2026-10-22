from typing import Annotated

from fastapi import APIRouter, Query

from kupto.deps import CurrentHousehold, CurrentUser, SessionDep
from kupto.history import service
from kupto.history.schemas import ProductOut, TripPageOut, product_out, trip_out
from kupto.lists import category_order

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("")
async def list_trips(
    user: CurrentUser,
    household: CurrentHousehold,
    session: SessionDep,
    before: Annotated[int | None, Query(description="`next_cursor` z poprzedniej strony")] = None,
    limit: Annotated[int, Query(ge=1, le=service.MAX_PAGE_SIZE)] = service.DEFAULT_PAGE_SIZE,
) -> TripPageOut:
    """Zakończenia zakupów gospodarstwa od najnowszych, stronicowane kursorem."""
    page = await service.list_trips(session, household, before, limit)
    logins = await service.logins(
        session,
        [trip.finished_by_id for trip in page.trips]
        + [item.bought_by_id for trip in page.trips for item in trip.items]
        + [need.user_id for trip in page.trips for item in trip.items for need in item.needs],
    )
    order = await category_order.get_order(session, user)
    return TripPageOut(
        trips=[trip_out(trip, order, logins) for trip in page.trips],
        next_cursor=page.next_cursor,
    )


@router.get("/products")
async def search_products(
    _: CurrentUser,
    household: CurrentHousehold,
    session: SessionDep,
    q: Annotated[str, Query(min_length=1, max_length=100)],
) -> list[ProductOut]:
    """Kiedy i kto ostatnio kupił produkty pasujące do frazy (bez wielkości liter i ogonków)."""
    matches = await service.search_products(session, household, q)
    logins = await service.logins(session, [m.last.bought_by_id for m in matches])
    return [product_out(m.last, m.times_bought, logins) for m in matches]

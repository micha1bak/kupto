"""„To co zwykle” — heurystyka `usual_missing` na przygotowanej historii i endpoint API."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from kupto.history.usual import usual_missing
from kupto.households import service as households
from kupto.lists import service as lists
from kupto.lists.service import NeedInput
from kupto.models import Category, Household, PurchasedItem, PurchasedNeed, ShoppingTrip, Unit, User

NOW = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
DAIRY = Category("Nabiał")


def days_ago(days: float) -> datetime:
    return NOW - timedelta(days=days)


async def add_trip(session, household, finished_at, *products):
    """Zakończenie zakupów; produkt to nazwa albo (nazwa, [(ilość, jednostka), ...])."""
    items = []
    for product in products:
        name, quantities = (product, []) if isinstance(product, str) else product
        items.append(
            PurchasedItem(
                name=name,
                normalized_name=name.lower(),
                category=DAIRY,
                bought_at=finished_at,
                needs=[
                    PurchasedNeed(
                        amount=Decimal(str(a)) if a is not None else None,
                        unit=Unit(u) if u else None,
                        requested_at=finished_at,
                    )
                    for a, u in quantities
                ],
            )
        )
    session.add(ShoppingTrip(household_id=household.id, finished_at=finished_at, items=items))
    await session.commit()


async def weekly(session, household, product, last_days_ago=7, times=4):
    for i in range(times):
        await add_trip(session, household, days_ago(last_days_ago + 7 * i), product)


def names(suggestions):
    return [s.name for s in suggestions]


@pytest.fixture
async def homes(session):
    ala, ewa = User(login="ala", password_hash="x"), User(login="ewa", password_hash="x")
    session.add_all([ala, ewa])
    await session.commit()
    return (
        await households.create_household(session, ala, "Dom"),
        await households.create_household(session, ewa, "Sąsiedzi"),
    )


async def test_regular_product_that_is_due_is_suggested(session, homes):
    home, _ = homes
    await weekly(session, home, ("mleko", [(2, "l")]))

    (milk,) = await usual_missing(session, home, NOW)

    assert milk.name == "mleko"
    assert milk.category == DAIRY
    assert (milk.amount, milk.unit) == (Decimal(2), Unit("l"))
    assert milk.times_bought == 4
    assert milk.typical_interval == timedelta(days=7)
    assert milk.last_bought_at == days_ago(7)
    assert milk.since_last == timedelta(days=7)
    assert milk.overdue == pytest.approx(1.0)


async def test_overdue_threshold(session, homes):
    home, _ = homes
    await weekly(session, home, "mleko", last_days_ago=5.7)  # 0,81 odstępu
    await weekly(session, home, "chleb", last_days_ago=5.5)  # 0,79 odstępu

    assert names(await usual_missing(session, home, NOW)) == ["mleko"]


async def test_bought_recently_is_not_suggested(session, homes):
    home, _ = homes
    await weekly(session, home, "mleko", last_days_ago=1)

    assert await usual_missing(session, home, NOW) == []


async def test_abandoned_product_is_not_suggested(session, homes):
    home, _ = homes
    await weekly(session, home, "mleko", last_days_ago=60)

    assert await usual_missing(session, home, NOW) == []


async def test_history_older_than_a_year_is_ignored(session, homes):
    home, _ = homes
    await add_trip(session, home, days_ago(400), "mleko")
    await add_trip(session, home, days_ago(393), "mleko")
    await add_trip(session, home, days_ago(7), "mleko")

    assert await usual_missing(session, home, NOW) == []


async def test_cold_start_needs_three_purchases(session, homes):
    home, _ = homes
    assert await usual_missing(session, home, NOW) == []

    await weekly(session, home, "mleko", times=2)
    assert await usual_missing(session, home, NOW) == []

    await add_trip(session, home, days_ago(21), "mleko")
    assert names(await usual_missing(session, home, NOW)) == ["mleko"]


async def test_typical_interval_is_the_median(session, homes):
    home, _ = homes
    # Odstępy 7, 7 i 30 dni (wyjazd) — mediana 7, więc mleko jest „na czasie” po tygodniu.
    for days in (51, 44, 14, 7):
        await add_trip(session, home, days_ago(days), "mleko")

    (milk,) = await usual_missing(session, home, NOW)

    assert milk.typical_interval == timedelta(days=7)


async def test_same_day_trips_count_as_at_least_one_day(session, homes):
    home, _ = homes
    for hours in (30, 29, 28):
        await add_trip(session, home, NOW - timedelta(hours=hours), "mleko")

    (milk,) = await usual_missing(session, home, NOW)

    assert milk.typical_interval == timedelta(days=1)


async def test_typical_quantity(session, homes):
    home, _ = homes
    # Litry w trzech zakupach (sumy 2, 3, 1 → mediana 2), sztuki tylko raz.
    for days, quantities in [
        (28, [(1, "l"), (1, "l")]),
        (21, [(3, "l")]),
        (14, [(1, "l"), (2, "szt")]),
        (7, [(None, None)]),
    ]:
        await add_trip(session, home, days_ago(days), ("mleko", quantities))

    (milk,) = await usual_missing(session, home, NOW)

    assert (milk.amount, milk.unit) == (Decimal(2), Unit("l"))


async def test_without_quantities_there_is_no_typical_amount(session, homes):
    home, _ = homes
    await weekly(session, home, "chleb")

    (bread,) = await usual_missing(session, home, NOW)

    assert (bread.amount, bread.unit) == (None, None)


async def test_most_overdue_first(session, homes):
    home, _ = homes
    await weekly(session, home, "mleko", last_days_ago=7)
    await weekly(session, home, "chleb", last_days_ago=14)

    assert names(await usual_missing(session, home, NOW)) == ["chleb", "mleko"]


async def test_products_on_the_list_are_skipped(session, homes):
    home, _ = homes
    await weekly(session, home, "mleko")
    await weekly(session, home, "chleb")
    user = await session.get(User, home.owner_id)
    await lists.add_needs(session, home, user, [NeedInput(name="Mleko")])

    assert names(await usual_missing(session, home, NOW)) == ["chleb"]


async def test_bought_item_still_on_the_list_is_skipped(session, homes):
    home, _ = homes
    await weekly(session, home, "mleko")
    user = await session.get(User, home.owner_id)
    (added,) = await lists.add_needs(session, home, user, [NeedInput(name="mleko")])
    shopping_list = await lists.get_list(session, home)
    await lists.set_bought(session, home, user, [shopping_list.items[0].id], bought=True)

    assert added.item_name == "mleko"
    assert await usual_missing(session, home, NOW) == []


async def test_households_are_isolated(session, homes):
    home, neighbours = homes
    await weekly(session, neighbours, "kawa")
    await weekly(session, home, "mleko")

    assert names(await usual_missing(session, home, NOW)) == ["mleko"]
    assert names(await usual_missing(session, neighbours, NOW)) == ["kawa"]


async def household_id(client) -> int:
    return (await client.get("/api/households/me")).json()["id"]


async def test_usual_api(household_with, session):
    ala, ola = await household_with("ala", "ola")
    home = await session.get(Household, await household_id(ala))
    now = datetime.now(UTC)
    for days in (28, 21, 14, 7):
        await add_trip(session, home, now - timedelta(days=days), ("mleko", [(2, "l")]))

    response = await ola.get("/api/history/usual")

    assert response.status_code == 200
    (milk,) = response.json()
    assert milk["name"] == "mleko"
    assert milk["category"] == "Nabiał"
    assert (milk["amount"], milk["unit"]) == (2.0, "l")
    assert milk["times_bought"] == 4
    assert milk["typical_interval_days"] == 7.0
    assert milk["overdue"] == pytest.approx(1.0, abs=0.01)

    await ala.post("/api/list/needs", json={"name": "mleko", "amount": 2, "unit": "l"})

    assert (await ola.get("/api/history/usual")).json() == []


async def test_usual_api_requires_login_and_household(client, login_as):
    assert (await client.get("/api/history/usual")).status_code == 401
    ala = await login_as("ala")
    assert (await ala.get("/api/history/usual")).status_code == 409

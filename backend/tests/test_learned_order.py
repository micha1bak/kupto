"""Kolejność wyuczona z historii odhaczeń — scenariusze ze specyfikacji zmiany learned-order."""

from datetime import UTC, datetime, timedelta
from itertools import count

import pytest

from kupto.households import service as households
from kupto.lists import category_order
from kupto.lists.learned_order import NOTHING, learn, learned_order
from kupto.lists.product_order import product_base_order
from kupto.models import Category, PurchasedItem, ShoppingTrip, User

BREAD, DAIRY, HOUSEHOLD = Category.BREAD, Category.DAIRY, Category.HOUSEHOLD
PRODUCTS = {
    "chleb": BREAD,
    "mleko": DAIRY,
    "ser": DAIRY,
    "jogurt": DAIRY,
    "płyn do naczyń": HOUSEHOLD,
}
START = datetime(2026, 1, 1, tzinfo=UTC)
_days = count()


async def trip(session, household, *passes):
    """Zakończenie zakupów; przejście = (użytkownik, nazwy w kolejności odhaczania)."""
    finished_at = START + timedelta(days=next(_days))
    items = [
        PurchasedItem(
            name=name,
            normalized_name=name,
            category=PRODUCTS[name],
            bought_at=finished_at - timedelta(minutes=30) + timedelta(minutes=minute),
            bought_by_id=user.id,
        )
        for user, names in passes
        for minute, name in enumerate(names)
    ]
    session.add(ShoppingTrip(household_id=household.id, finished_at=finished_at, items=items))
    await session.commit()


async def times(n, session, household, *passes):
    for _ in range(n):
        await trip(session, household, *passes)


async def categories(session, user, *among):
    """Kolejność kategorii użytkownika zawężona do `among`."""
    order = await category_order.get_order(session, user)
    return [c for c in order.categories if c in among]


@pytest.fixture
async def home(session):
    ala, ewa, ola = (User(login=login, password_hash="x") for login in ("ala", "ewa", "ola"))
    session.add_all([ala, ewa, ola])
    await session.commit()
    house = await households.create_household(session, ala, "Dom")
    await households.add_member(session, ala, house, "ewa")
    neighbours = await households.create_household(session, ola, "Sąsiedzi")
    return ala, ewa, ola, house, neighbours


def test_learn_takes_median_of_relative_places():
    x, y, z = Category.DAIRY, Category.BREAD, Category.OTHER
    passes = [
        [("a", x), ("b", y), ("c", x)],
        [("b", y), ("a", x), ("d", z)],
        [("a", x), ("c", x)],
    ]

    learned = learn(passes)

    # a: 0, ½, 0; b: ½, 0; c: 1, 1; d — tylko raz, więc bez wyniku.
    assert learned.products == {"a": 0.0, "b": 0.25, "c": 1.0}
    # Kategoria w przejściu = średnia miejsc jej pozycji: x — ½, ½, ½; y — ½, 0; z — raz.
    assert learned.categories == {x: 0.5, y: 0.25}


async def test_order_from_own_check_offs(session, home):
    ala, *_, house, _ = home
    await times(3, session, house, (ala, ["płyn do naczyń", "mleko", "chleb"]))

    assert await categories(session, ala, BREAD, DAIRY, HOUSEHOLD) == [HOUSEHOLD, DAIRY, BREAD]


async def test_products_from_check_offs_and_unknown_product_keeps_its_place(session, home):
    ala, *_, house, _ = home
    await times(3, session, house, (ala, ["ser", "mleko", "chleb"]))

    learned = await learned_order(session, ala)

    assert product_base_order(DAIRY, ["jogurt", "mleko", "ser"], learned.products) == [
        "jogurt",
        "ser",
        "mleko",
    ]


async def test_own_passes_win_over_household(session, home):
    ala, ewa, *_, house, _ = home
    await times(3, session, house, (ala, ["chleb", "mleko"]), (ewa, ["mleko", "chleb"]))

    assert await categories(session, ala, BREAD, DAIRY) == [BREAD, DAIRY]
    assert await categories(session, ewa, BREAD, DAIRY) == [DAIRY, BREAD]


async def test_cold_start_learns_from_household(session, home):
    ala, ewa, *_, house, _ = home
    await times(3, session, house, (ala, ["płyn do naczyń", "chleb"]))
    await times(2, session, house, (ewa, ["chleb", "mleko"]))

    # ewa ma tylko 2 własne przejścia — uczy się z 5 przejść gospodarstwa.
    assert await categories(session, ewa, BREAD, HOUSEHOLD) == [HOUSEHOLD, BREAD]


async def test_cold_start_without_enough_history_is_base_order(session, home):
    ala, ewa, *_, house, _ = home
    await times(2, session, house, (ala, ["płyn do naczyń", "chleb"]))
    # Przejścia z jedną pozycją nie niosą kolejności.
    await times(3, session, house, (ewa, ["płyn do naczyń"]), (ala, ["mleko"]))

    assert await learned_order(session, ewa) == NOTHING
    assert (await category_order.get_order(session, ewa)).categories == list(Category)


async def test_other_household_history_is_ignored(session, home):
    ala, _, ola, _, neighbours = home
    await times(5, session, neighbours, (ola, ["płyn do naczyń", "chleb"]))

    assert await learned_order(session, ala) == NOTHING


async def test_one_unusual_pass_does_not_change_order(session, home):
    ala, *_, house, _ = home
    await times(4, session, house, (ala, ["chleb", "mleko"]))
    await trip(session, house, (ala, ["mleko", "chleb"]))

    assert await categories(session, ala, BREAD, DAIRY) == [BREAD, DAIRY]


async def test_only_last_passes_count(session, home):
    ala, *_, house, _ = home
    await times(10, session, house, (ala, ["chleb", "mleko"]))
    await times(10, session, house, (ala, ["mleko", "chleb"]))

    # Z 20 przejść byłby remis (kolejność zbioru: Pieczywo przed Nabiałem); liczy się 10 ostatnich.
    assert await categories(session, ala, BREAD, DAIRY) == [DAIRY, BREAD]


async def test_pinned_category_wins_over_learned_order(session, home):
    ala, *_, house, _ = home
    await times(3, session, house, (ala, ["płyn do naczyń", "mleko", "chleb"]))
    first = (await category_order.get_order(session, ala)).categories[0]

    await category_order.pin(session, ala, BREAD, after=None, before=first)

    order = await category_order.get_order(session, ala)
    assert order.categories[0] == BREAD
    assert order.pinned == {BREAD}
    assert [c for c in order.categories if c in (BREAD, DAIRY, HOUSEHOLD)] == [
        BREAD,
        HOUSEHOLD,
        DAIRY,
    ]


# --- API ---


async def shop(client, *names):
    """Dodaje produkty, odhacza je w podanej kolejności i kończy zakupy."""
    for name in names:
        response = await client.post(
            "/api/list/needs", json={"name": name, "category": PRODUCTS[name].value}
        )
        assert response.status_code == 201, response.text
    by_name = await ids(client)
    for name in names:
        response = await client.post(f"/api/list/items/{by_name[name]}/bought")
        assert response.status_code == 200, response.text
    assert (await client.post("/api/list/finish")).status_code == 200


async def ids(client):
    body = (await client.get("/api/list")).json()
    return {i["name"]: i["id"] for g in body["groups"] for i in g["items"]}


def layout(body):
    return [
        (g["category"], [i["name"] + ("*" if i["pinned"] else "") for i in g["items"]])
        for g in body["groups"]
    ]


async def add(client, *names):
    for name in names:
        response = await client.post(
            "/api/list/needs", json={"name": name, "category": PRODUCTS[name].value}
        )
        assert response.status_code == 201, response.text


async def test_members_with_different_habits_api(household_with):
    ala, ewa = await household_with("ala", "ewa")
    for _ in range(3):
        await shop(ala, "chleb", "ser", "mleko")
        await shop(ewa, "mleko", "ser", "chleb")
    await add(ala, "chleb", "mleko", "ser", "jogurt")

    assert layout((await ala.get("/api/list")).json()) == [
        ("Pieczywo", ["chleb"]),
        ("Nabiał", ["jogurt", "ser", "mleko"]),
    ]
    assert layout((await ewa.get("/api/list")).json()) == [
        ("Nabiał", ["jogurt", "mleko", "ser"]),
        ("Pieczywo", ["chleb"]),
    ]


async def test_check_offs_do_not_reorder_until_finish_api(household_with):
    (ala,) = await household_with("ala")
    for _ in range(3):
        await shop(ala, "chleb", "mleko")
    await add(ala, "chleb", "mleko")
    expected = [("Pieczywo", ["chleb"]), ("Nabiał", ["mleko"])]

    by_name = await ids(ala)
    for name in ("mleko", "chleb"):
        body = (await ala.post(f"/api/list/items/{by_name[name]}/bought")).json()
        assert layout(body) == expected


async def test_pinned_product_on_learned_order_api(household_with):
    (ala,) = await household_with("ala")
    for _ in range(3):
        await shop(ala, "ser", "mleko", "jogurt")
    await add(ala, "jogurt", "mleko", "ser")
    by_name = await ids(ala)
    assert layout((await ala.get("/api/list")).json()) == [("Nabiał", ["ser", "mleko", "jogurt"])]

    response = await ala.put(
        f"/api/list/items/{by_name['jogurt']}/order",
        json={"after": None, "before": by_name["ser"]},
    )

    assert response.status_code == 200, response.text
    assert layout(response.json()) == [("Nabiał", ["jogurt*", "ser", "mleko"])]

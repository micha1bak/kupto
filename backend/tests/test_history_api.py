from datetime import UTC, datetime

from sqlalchemy import update

from kupto.models import ShoppingTrip


def item_id(body, name):
    return next(i["id"] for g in body["groups"] for i in g["items"] if i["name"] == name)


async def buy(client, *names, category=None):
    """Zgłasza produkty (jeśli trzeba) i oznacza je jako kupione przez `client`."""
    for name in names:
        payload = {"name": name} | ({"category": category} if category else {})
        body = (await client.post("/api/list/needs", json=payload)).json()
        response = await client.post(f"/api/list/items/{item_id(body, name)}/bought")
        assert response.status_code == 200, response.text


async def trip(client, *names, category=None):
    """Jedno zakończenie zakupów z podanymi produktami."""
    await buy(client, *names, category=category)
    response = await client.post("/api/list/finish")
    assert response.status_code == 200, response.text


def trip_items(trip):
    return [i["name"] for g in trip["groups"] for i in g["items"]]


async def test_empty_history(household_with):
    (ala,) = await household_with("ala")

    response = await ala.get("/api/history")

    assert response.status_code == 200
    assert response.json() == {"trips": [], "next_cursor": None}


async def test_history_requires_household(login_as):
    ala = await login_as("ala")

    assert (await ala.get("/api/history")).status_code == 409
    assert (await ala.get("/api/history/products", params={"q": "mleko"})).status_code == 409


async def test_history_requires_login(client):
    assert (await client.get("/api/history")).status_code == 401


async def test_trip_details(household_with):
    ala, ola = await household_with("ala", "ola")
    milk = {"name": "mleko", "amount": 2, "unit": "l", "note": "bez laktozy", "category": "Nabiał"}
    await ala.post("/api/list/needs", json=milk)
    await ola.post("/api/list/needs", json={"name": "mleko", "amount": 1, "unit": "l"})
    bread = {"name": "chleb", "category": "Pieczywo"}
    body = (await ala.post("/api/list/needs", json=bread)).json()
    await ola.post(f"/api/list/items/{item_id(body, 'mleko')}/bought")
    await ala.post(f"/api/list/items/{item_id(body, 'chleb')}/bought")
    await ala.post("/api/list/finish")

    (finished,) = (await ola.get("/api/history")).json()["trips"]

    assert finished["finished_by"] == "ala"
    assert finished["item_count"] == 2
    assert [g["category"] for g in finished["groups"]] == ["Pieczywo", "Nabiał"]
    (milk,) = finished["groups"][1]["items"]
    assert milk["name"] == "mleko"
    assert milk["bought_by"] == "ola"
    assert milk["bought_at"] is not None
    assert milk["quantities"] == [{"amount": 3.0, "unit": "l"}]
    assert [(n["name"], n["amount"], n["unit"], n["note"]) for n in milk["needs"]] == [
        ("ala", 2.0, "l", "bez laktozy"),
        ("ola", 1.0, "l", None),
    ]
    assert "price" not in str(finished) and "amount_paid" not in str(finished)


async def test_groups_follow_users_category_order(household_with):
    (ala,) = await household_with("ala")
    await buy(ala, "mleko", category="Nabiał")
    await buy(ala, "chleb", category="Pieczywo")
    await ala.post("/api/list/finish")
    await ala.put("/api/list/category-order/Nabiał", json={"before": "Warzywa i owoce"})

    (finished,) = (await ala.get("/api/history")).json()["trips"]

    assert [g["category"] for g in finished["groups"]] == ["Nabiał", "Pieczywo"]


async def test_newest_trip_first(household_with):
    ala, ola = await household_with("ala", "ola")
    await trip(ala, "chleb")
    await trip(ola, "mleko")

    trips = (await ala.get("/api/history")).json()["trips"]

    assert [(t["finished_by"], trip_items(t)) for t in trips] == [
        ("ola", ["mleko"]),
        ("ala", ["chleb"]),
    ]


async def test_pagination_without_duplicates_or_gaps(household_with, session):
    (ala,) = await household_with("ala")
    for n in range(5):
        await trip(ala, f"produkt {n}")
    # Dwa zakończenia o tej samej chwili — kolejność rozstrzyga id.
    same_time = datetime(2026, 1, 1, tzinfo=UTC)
    await session.execute(
        update(ShoppingTrip).where(ShoppingTrip.id.in_([2, 3])).values(finished_at=same_time)
    )
    await session.commit()

    seen = []
    cursor = None
    pages = 0
    while True:
        params = {"limit": 2} | ({"before": cursor} if cursor is not None else {})
        page = (await ala.get("/api/history", params=params)).json()
        pages += 1
        seen += [t["id"] for t in page["trips"]]
        cursor = page["next_cursor"]
        if cursor is None:
            break

    assert pages == 3
    assert seen == [5, 4, 1, 3, 2]


async def test_last_page_exactly_full_has_no_cursor(household_with):
    (ala,) = await household_with("ala")
    await trip(ala, "chleb")
    await trip(ala, "mleko")

    page = (await ala.get("/api/history", params={"limit": 2})).json()

    assert len(page["trips"]) == 2
    assert page["next_cursor"] is None


async def test_limit_is_validated(household_with):
    (ala,) = await household_with("ala")

    assert (await ala.get("/api/history", params={"limit": 0})).status_code == 422
    assert (await ala.get("/api/history", params={"limit": 51})).status_code == 422


async def test_history_is_isolated_between_households(household_with):
    (ala,) = await household_with("ala")
    (ewa,) = await household_with("ewa", name="Inny dom")
    await trip(ala, "kawa")
    await trip(ewa, "herbata")

    ala_trips = (await ala.get("/api/history")).json()["trips"]
    ewa_trips = (await ewa.get("/api/history")).json()["trips"]

    assert [trip_items(t) for t in ala_trips] == [["kawa"]]
    assert [trip_items(t) for t in ewa_trips] == [["herbata"]]
    # Kursor z cudzego gospodarstwa nie zdradza niczego.
    response = await ewa.get("/api/history", params={"before": ala_trips[0]["id"]})
    assert response.status_code == 404


async def test_search_returns_last_purchase_and_count(household_with):
    ala, ola = await household_with("ala", "ola")
    await trip(ola, "kawa")
    await ala.post("/api/list/needs", json={"name": "kawa", "amount": 2, "unit": "opak"})
    await trip(ala, "kawa")
    await trip(ola, "kawior")

    results = (await ala.get("/api/history/products", params={"q": "KAWA"})).json()

    assert len(results) == 1
    (coffee,) = results
    assert coffee["name"] == "kawa"
    assert coffee["last_bought_by"] == "ala"
    assert coffee["times_bought"] == 2
    assert coffee["last_quantities"] == [{"amount": 2.0, "unit": "opak"}]
    trips = (await ala.get("/api/history")).json()["trips"]
    assert coffee["last_trip_id"] == trips[1]["id"]


async def test_search_most_recent_first(household_with):
    (ala,) = await household_with("ala")
    await trip(ala, "ser żółty")
    await trip(ala, "ser biały")

    results = (await ala.get("/api/history/products", params={"q": "ser"})).json()

    assert [r["name"] for r in results] == ["ser biały", "ser żółty"]


async def test_search_ignores_polish_characters(household_with):
    (ala,) = await household_with("ala")
    await trip(ala, "Żółty ser")

    by_ascii = (await ala.get("/api/history/products", params={"q": "zolty"})).json()
    by_polish = (await ala.get("/api/history/products", params={"q": "ŻÓŁTY"})).json()

    assert [r["name"] for r in by_ascii] == ["Żółty ser"]
    assert by_polish == by_ascii


async def test_search_without_results(household_with):
    (ala,) = await household_with("ala")
    await trip(ala, "chleb")

    response = await ala.get("/api/history/products", params={"q": "kawa"})

    assert response.status_code == 200
    assert response.json() == []


async def test_search_treats_wildcards_literally(household_with):
    (ala,) = await household_with("ala")
    await trip(ala, "chleb")

    for q in ("%", "_", "ch_eb"):
        assert (await ala.get("/api/history/products", params={"q": q})).json() == []


async def test_search_requires_phrase(household_with):
    (ala,) = await household_with("ala")

    assert (await ala.get("/api/history/products", params={"q": "   "})).status_code == 422
    assert (await ala.get("/api/history/products")).status_code == 422


async def test_search_is_isolated_between_households(household_with):
    (ala,) = await household_with("ala")
    (ewa,) = await household_with("ewa", name="Inny dom")
    await trip(ewa, "kawa")

    assert (await ala.get("/api/history/products", params={"q": "kawa"})).json() == []
    assert len((await ewa.get("/api/history/products", params={"q": "kawa"})).json()) == 1

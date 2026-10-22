from sqlalchemy import select

from kupto.models import Category, User


def groups(body):
    return {g["category"]: [i["name"] for i in g["items"]] for g in body["groups"]}


def item(body, name):
    return next(i for g in body["groups"] for i in g["items"] if i["name"] == name)


async def test_members_see_the_same_list(household_with):
    ala, ola = await household_with("ala", "ola")
    await ala.post("/api/list/needs", json={"name": "mleko", "category": "Nabiał"})

    assert (await ala.get("/api/list")).json() == (await ola.get("/api/list")).json()


async def test_list_requires_household(login_as):
    ala = await login_as("ala")

    assert (await ala.get("/api/list")).status_code == 409


async def test_add_need_with_amount_unit_and_note(household_with):
    (ala,) = await household_with("ala")

    response = await ala.post(
        "/api/list/needs",
        json={
            "name": "mleko",
            "amount": 2,
            "unit": "l",
            "note": "bez laktozy",
            "category": "Nabiał",
        },
    )

    assert response.status_code == 201
    milk = item(response.json(), "mleko")
    assert milk["quantities"] == [{"amount": 2.0, "unit": "l"}]
    assert [(n["login"], n["note"]) for n in milk["needs"]] == [("ala", "bez laktozy")]


async def test_needs_from_two_members_are_merged(household_with):
    ala, ola = await household_with("ala", "ola")
    await ala.post("/api/list/needs", json={"name": "mleko", "amount": 1, "unit": "l"})

    body = (
        await ola.post("/api/list/needs", json={"name": " Mleko ", "amount": 2, "unit": "l"})
    ).json()

    milk = item(body, "mleko")
    assert milk["quantities"] == [{"amount": 3.0, "unit": "l"}]
    assert [n["login"] for n in milk["needs"]] == ["ala", "ola"]


async def test_different_units_are_shown_separately(household_with):
    (ala,) = await household_with("ala")
    await ala.post("/api/list/needs", json={"name": "jabłka", "amount": 2, "unit": "szt"})

    body = (
        await ala.post("/api/list/needs", json={"name": "jabłka", "amount": 1, "unit": "kg"})
    ).json()

    assert item(body, "jabłka")["quantities"] == [
        {"amount": 2.0, "unit": "szt"},
        {"amount": 1.0, "unit": "kg"},
    ]


async def test_list_is_grouped_by_category_in_fixed_order(household_with):
    (ala,) = await household_with("ala")
    for name, category in [
        ("płyn do naczyń", "Chemia i higiena"),
        ("ser żółty", "Nabiał"),
        ("mleko", "Nabiał"),
    ]:
        await ala.post("/api/list/needs", json={"name": name, "category": category})

    body = (await ala.get("/api/list")).json()

    assert groups(body) == {
        "Nabiał": ["mleko", "ser żółty"],
        "Chemia i higiena": ["płyn do naczyń"],
    }
    assert [g["category"] for g in body["groups"]] == ["Nabiał", "Chemia i higiena"]


async def test_manual_need_without_category(household_with):
    (ala,) = await household_with("ala")
    await ala.post("/api/list/needs", json={"name": "mleko", "category": "Nabiał"})
    milk_id = item((await ala.get("/api/list")).json(), "mleko")["id"]
    await ala.delete(f"/api/list/items/{milk_id}")

    body = (await ala.post("/api/list/needs", json={"name": "mleko"})).json()
    body = (await ala.post("/api/list/needs", json={"name": "coś nowego"})).json()

    assert groups(body) == {"Nabiał": ["mleko"], "Inne": ["coś nowego"]}


async def test_need_validation(household_with):
    (ala,) = await household_with("ala")

    for payload in [
        {"name": ""},
        {"name": "   "},
        {"name": "x" * 101},
        {"name": "mleko", "amount": 0},
        {"name": "mleko", "unit": "beczka"},
        {"name": "mleko", "category": "Elektronika"},
    ]:
        assert (await ala.post("/api/list/needs", json=payload)).status_code == 422, payload


async def test_mark_and_unmark_bought(household_with):
    ala, ola = await household_with("ala", "ola")
    body = (await ala.post("/api/list/needs", json={"name": "mleko"})).json()
    milk_id = item(body, "mleko")["id"]

    body = (await ola.post(f"/api/list/items/{milk_id}/bought")).json()
    milk = item(body, "mleko")
    assert (milk["bought"], milk["bought_by"]) == (True, "ola")
    assert milk["bought_at"] is not None

    body = (await ala.delete(f"/api/list/items/{milk_id}/bought")).json()
    assert item(body, "mleko")["bought"] is False


async def test_update_and_withdraw_own_need(household_with):
    ala, ola = await household_with("ala", "ola")
    await ala.post("/api/list/needs", json={"name": "mleko", "amount": 1, "unit": "l"})
    body = (
        await ola.post("/api/list/needs", json={"name": "mleko", "amount": 2, "unit": "l"})
    ).json()
    ala_need, ola_need = item(body, "mleko")["needs"]

    body = (await ala.patch(f"/api/list/needs/{ala_need['id']}", json={"amount": 3})).json()
    assert item(body, "mleko")["quantities"] == [{"amount": 5.0, "unit": "l"}]

    assert (await ala.delete(f"/api/list/needs/{ola_need['id']}")).status_code == 403
    body = (await ala.delete(f"/api/list/needs/{ala_need['id']}")).json()
    assert item(body, "mleko")["quantities"] == [{"amount": 2.0, "unit": "l"}]

    body = (await ola.delete(f"/api/list/needs/{ola_need['id']}")).json()
    assert body["groups"] == []


async def test_remove_item(household_with):
    (ala,) = await household_with("ala")
    body = (await ala.post("/api/list/needs", json={"name": "chleb"})).json()

    body = (await ala.delete(f"/api/list/items/{item(body, 'chleb')['id']}")).json()

    assert body["groups"] == []


async def test_finish_shopping(household_with, session, purchase_history):
    ala, ola = await household_with("ala", "ola")
    await ala.post("/api/list/needs", json={"name": "chleb"})
    body = (await ala.post("/api/list/needs", json={"name": "mleko", "category": "Nabiał"})).json()
    await ola.post(f"/api/list/items/{item(body, 'mleko')['id']}/bought")

    response = await ola.post("/api/list/finish")

    assert response.status_code == 200
    assert groups(response.json()) == {"Inne": ["chleb"]}
    assert (await ala.get("/api/list")).json() == response.json()
    users = {u.login: u.id for u in await session.scalars(select(User))}
    (trip,) = await purchase_history()
    assert trip.finished_by_id == users["ola"]
    (milk,) = trip.items
    assert (milk.name, milk.category, milk.bought_by_id) == ("mleko", Category.DAIRY, users["ola"])
    assert [n.user_id for n in milk.needs] == [users["ala"]]


async def test_finish_shopping_with_nothing_bought(household_with, purchase_history):
    (ala,) = await household_with("ala")
    await ala.post("/api/list/needs", json={"name": "chleb"})

    body = (await ala.post("/api/list/finish")).json()

    assert groups(body) == {"Inne": ["chleb"]}
    assert await purchase_history() == []


async def test_other_household_items_are_not_accessible(household_with):
    (ala,) = await household_with("ala")
    (ewa,) = await household_with("ewa", name="Inny dom")
    body = (await ala.post("/api/list/needs", json={"name": "mleko"})).json()
    milk = item(body, "mleko")

    assert (await ewa.delete(f"/api/list/items/{milk['id']}")).status_code == 404
    assert (await ewa.post(f"/api/list/items/{milk['id']}/bought")).status_code == 404
    assert (
        await ewa.patch(f"/api/list/needs/{milk['needs'][0]['id']}", json={"amount": 9})
    ).status_code == 404
    assert (await ewa.get("/api/list")).json()["groups"] == []
    assert item((await ala.get("/api/list")).json(), "mleko")["bought"] is False

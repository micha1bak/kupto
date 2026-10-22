"""Ręczna kolejność produktów w kategorii — scenariusze ze specyfikacji zmiany product-order."""

import random

import pytest

DAIRY = "Nabiał"


async def add(client, *names, category=DAIRY):
    for name in names:
        response = await client.post("/api/list/needs", json={"name": name, "category": category})
        assert response.status_code == 201, response.text


def group(body, category=DAIRY):
    """Nazwy pozycji grupy w kolejności z odpowiedzi; przypięte z dopiskiem „*”."""
    for g in body["groups"]:
        if g["category"] == category:
            return [i["name"] + ("*" if i["pinned"] else "") for i in g["items"]]
    return []


def names(body, category=DAIRY):
    return [name.rstrip("*") for name in group(body, category)]


async def ids(client):
    body = (await client.get("/api/list")).json()
    return {i["name"]: i["id"] for g in body["groups"] for i in g["items"]}


async def move(client, name, after=None, before=None, *, expect=200):
    by_name = await ids(client)
    response = await client.put(
        f"/api/list/items/{by_name[name]}/order",
        json={
            "after": by_name[after] if after else None,
            "before": by_name[before] if before else None,
        },
    )
    assert response.status_code == expect, response.text
    return response.json()


async def remove(client, *names):
    by_name = await ids(client)
    for name in names:
        assert (await client.delete(f"/api/list/items/{by_name[name]}")).status_code == 200


async def finish_shopping(client):
    for item_id in (await ids(client)).values():
        assert (await client.post(f"/api/list/items/{item_id}/bought")).status_code == 200
    assert (await client.post("/api/list/finish")).status_code == 200


async def test_items_without_pins_are_alphabetical(household_with):
    (ala,) = await household_with("ala")
    await add(ala, "ser", "mleko", "jogurt")

    assert group((await ala.get("/api/list")).json()) == ["jogurt", "mleko", "ser"]


async def test_move_to_start_between_and_to_end(household_with):
    (ala,) = await household_with("ala")
    await add(ala, "ser", "mleko", "jogurt")

    assert group(await move(ala, "ser", before="jogurt")) == ["ser*", "jogurt", "mleko"]

    body = await move(ala, "ser", after="jogurt", before="mleko")
    assert group(body) == ["jogurt", "ser*", "mleko"]

    body = await move(ala, "jogurt", after="mleko")
    assert group(body) == ["ser*", "mleko", "jogurt*"]


async def test_item_moved_to_end_stays_last(household_with):
    (ala,) = await household_with("ala")
    await add(ala, "ser", "mleko", "jogurt")
    await move(ala, "jogurt", after="ser")

    await add(ala, "twaróg")

    assert group((await ala.get("/api/list")).json()) == ["mleko", "ser", "twaróg", "jogurt*"]


async def test_pinned_item_stays_behind_its_predecessor(household_with):
    (ala,) = await household_with("ala")
    await add(ala, "ser", "mleko", "jogurt")
    await move(ala, "ser", after="jogurt", before="mleko")

    await add(ala, "bita śmietana", "zsiadłe mleko")

    assert group((await ala.get("/api/list")).json()) == [
        "bita śmietana",
        "jogurt",
        "ser*",
        "mleko",
        "zsiadłe mleko",
    ]


async def test_new_item_does_not_push_a_pinned_one_from_the_start(household_with):
    (ala,) = await household_with("ala")
    await add(ala, "ser", "mleko", "jogurt")
    await move(ala, "ser", before="jogurt")

    await add(ala, "bita śmietana")

    assert names((await ala.get("/api/list")).json())[:2] == ["ser", "bita śmietana"]


async def test_next_pin_keeps_earlier_pins(household_with):
    (ala,) = await household_with("ala")
    await add(ala, "ser", "mleko", "jogurt")
    await move(ala, "ser", before="jogurt")

    body = await move(ala, "mleko", before="ser")

    assert group(body) == ["mleko*", "ser*", "jogurt"]


async def test_pin_works_when_the_product_is_added_again(household_with):
    (ala,) = await household_with("ala")
    await add(ala, "ser", "mleko", "jogurt")
    await move(ala, "ser", before="jogurt")
    await finish_shopping(ala)

    await add(ala, "jogurt", "Ser", "mleko")

    assert group((await ala.get("/api/list")).json()) == ["Ser*", "jogurt", "mleko"]


async def test_absent_pinned_items_keep_relative_order(household_with):
    (ala,) = await household_with("ala")
    await add(ala, "ser", "mleko", "jogurt")
    await move(ala, "ser", before="jogurt")
    await move(ala, "mleko", after="ser", before="jogurt")
    await move(ala, "jogurt", after="mleko")
    await remove(ala, "mleko")

    assert group((await ala.get("/api/list")).json()) == ["ser*", "jogurt*"]


async def test_order_is_per_user_and_content_is_shared(household_with):
    ala, ola = await household_with("ala", "ola")
    await add(ala, "ser", "mleko", "jogurt")
    await move(ala, "ser", before="jogurt")

    ala_body = (await ala.get("/api/list")).json()
    ola_body = (await ola.get("/api/list")).json()
    assert group(ala_body) == ["ser*", "jogurt", "mleko"]
    assert group(ola_body) == ["jogurt", "mleko", "ser"]

    def contents(body):
        return {
            g["category"]: sorted(
                ({k: v for k, v in i.items() if k != "pinned"} for i in g["items"]),
                key=lambda i: i["id"],
            )
            for g in body["groups"]
        }

    assert contents(ala_body) == contents(ola_body)


async def test_unpin_returns_item_to_alphabetical_place(household_with):
    (ala,) = await household_with("ala")
    await add(ala, "ser", "mleko", "jogurt")
    await move(ala, "ser", before="jogurt")
    await move(ala, "mleko", before="ser")
    by_name = await ids(ala)

    response = await ala.delete(f"/api/list/items/{by_name['ser']}/order")

    assert response.status_code == 200
    assert group(response.json()) == ["mleko*", "jogurt", "ser"]


async def test_category_pins_and_product_pins_work_together(household_with):
    (ala,) = await household_with("ala")
    await add(ala, "ser", "mleko")
    await add(ala, "chleb", "bułki", category="Pieczywo")
    await move(ala, "chleb", before="bułki")
    await ala.put("/api/list/category-order/Nabiał", json={"before": "Pieczywo"})

    body = (await ala.get("/api/list")).json()

    assert [g["category"] for g in body["groups"]] == ["Nabiał", "Pieczywo"]
    assert group(body, "Pieczywo") == ["chleb*", "bułki"]


async def test_invalid_moves(household_with):
    (ala,) = await household_with("ala")
    (ewa,) = await household_with("ewa", name="Inny dom")
    await add(ala, "ser", "mleko")
    await add(ala, "chleb", category="Pieczywo")
    await add(ewa, "kefir")

    await move(ala, "ser", after="ser", expect=400)
    await move(ala, "ser", after="chleb", before="mleko", expect=400)
    by_name = await ids(ala)
    ewa_ids = await ids(ewa)
    # Cudza pozycja — 404, także przy odpinaniu.
    response = await ala.put(f"/api/list/items/{ewa_ids['kefir']}/order", json={})
    assert response.status_code == 404
    assert (await ala.delete(f"/api/list/items/{ewa_ids['kefir']}/order")).status_code == 404
    # Sąsiad, którego nie ma (np. usunięty w międzyczasie), jest pomijany.
    response = await ala.put(
        f"/api/list/items/{by_name['ser']}/order", json={"after": 999999, "before": None}
    )
    assert group(response.json()) == ["mleko", "ser*"]
    response = await ala.put(
        f"/api/list/items/{by_name['ser']}/order",
        json={"after": 999999, "before": by_name["mleko"]},
    )
    assert group(response.json()) == ["ser*", "mleko"]
    response = await ala.put(
        f"/api/list/items/{by_name['mleko']}/order", json={"after": 999998, "before": 999999}
    )
    assert response.status_code == 409


async def test_product_order_requires_household(login_as):
    ala = await login_as("ala")

    assert (await ala.put("/api/list/items/1/order", json={})).status_code == 409
    assert (await ala.delete("/api/list/items/1/order")).status_code == 409


@pytest.mark.parametrize("seed", range(3))
async def test_random_moves_end_exactly_where_dropped(household_with, seed):
    """Każde upuszczenie daje dokładnie kolejność z widoku klienta, a usunięcie pozycji
    nie zmienia względnego układu pozostałych — niezależnie od historii przypięć."""
    rng = random.Random(seed)
    (ala,) = await household_with("ala")
    pool = ["jogurt", "kefir", "masło", "mleko", "ser", "twaróg", "śmietana", "maślanka"]
    await add(ala, *pool)
    order = names((await ala.get("/api/list")).json())

    for _ in range(25):
        if len(order) > 3 and rng.random() < 0.15:
            gone = rng.choice(order)
            await remove(ala, gone)
            order.remove(gone)
            assert names((await ala.get("/api/list")).json()) == order
            continue
        name = rng.choice(order)
        rest = [n for n in order if n != name]
        index = rng.randrange(len(rest) + 1)
        after = rest[index - 1] if index > 0 else None
        before = rest[index] if index < len(rest) else None
        expected = [*rest[:index], name, *rest[index:]]

        body = await move(ala, name, after=after, before=before)

        assert names(body) == expected
        order = expected

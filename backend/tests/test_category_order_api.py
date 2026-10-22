def categories(body):
    return [g["category"] for g in body["groups"]]


def pinned(body):
    return [g["category"] for g in body["groups"] if g["pinned"]]


async def add(client, *pairs):
    for name, category in pairs:
        response = await client.post("/api/list/needs", json={"name": name, "category": category})
        assert response.status_code == 201, response.text


BREAD_DAIRY_HOUSEHOLD = [
    ("płyn do naczyń", "Chemia i higiena"),
    ("mleko", "Nabiał"),
    ("chleb", "Pieczywo"),
]


async def test_list_without_pins_is_in_automatic_order(household_with):
    (ala,) = await household_with("ala")
    await add(ala, *BREAD_DAIRY_HOUSEHOLD)

    body = (await ala.get("/api/list")).json()

    assert categories(body) == ["Pieczywo", "Nabiał", "Chemia i higiena"]
    assert pinned(body) == []


async def test_move_to_start_between_and_to_end(household_with):
    (ala,) = await household_with("ala")
    await add(ala, *BREAD_DAIRY_HOUSEHOLD)

    response = await ala.put(
        "/api/list/category-order/Chemia i higiena", json={"after": None, "before": "Pieczywo"}
    )
    assert response.status_code == 200
    assert categories(response.json()) == ["Chemia i higiena", "Pieczywo", "Nabiał"]
    assert pinned(response.json()) == ["Chemia i higiena"]

    body = (
        await ala.put(
            "/api/list/category-order/Chemia i higiena",
            json={"after": "Pieczywo", "before": "Nabiał"},
        )
    ).json()
    assert categories(body) == ["Pieczywo", "Chemia i higiena", "Nabiał"]

    body = (
        await ala.put("/api/list/category-order/Pieczywo", json={"after": "Nabiał", "before": None})
    ).json()
    assert categories(body) == ["Chemia i higiena", "Nabiał", "Pieczywo"]
    assert set(pinned(body)) == {"Chemia i higiena", "Pieczywo"}


async def test_pinned_category_keeps_its_place_when_new_categories_appear(household_with):
    (ala,) = await household_with("ala")
    await add(ala, *BREAD_DAIRY_HOUSEHOLD)
    await ala.put("/api/list/category-order/Chemia i higiena", json={"before": "Pieczywo"})
    await ala.put("/api/list/category-order/Pieczywo", json={"after": "Nabiał"})

    await add(ala, ("jabłka", "Warzywa i owoce"), ("baterie", "Inne"))

    body = (await ala.get("/api/list")).json()
    assert categories(body) == [
        "Chemia i higiena",
        "Warzywa i owoce",
        "Nabiał",
        "Inne",
        "Pieczywo",
    ]


async def test_order_is_per_user_and_content_is_shared(household_with):
    ala, ola = await household_with("ala", "ola")
    await add(ala, *BREAD_DAIRY_HOUSEHOLD)

    await ala.put("/api/list/category-order/Chemia i higiena", json={"before": "Pieczywo"})

    ala_body = (await ala.get("/api/list")).json()
    ola_body = (await ola.get("/api/list")).json()
    assert categories(ala_body) == ["Chemia i higiena", "Pieczywo", "Nabiał"]
    assert categories(ola_body) == ["Pieczywo", "Nabiał", "Chemia i higiena"]
    assert pinned(ola_body) == []

    def by_category(body):
        return {g["category"]: g["items"] for g in body["groups"]}

    assert by_category(ala_body) == by_category(ola_body)


async def test_pins_survive_a_new_session(household_with, login_as):
    (ala,) = await household_with("ala")
    await add(ala, *BREAD_DAIRY_HOUSEHOLD)
    await ala.put("/api/list/category-order/Nabiał", json={"before": "Pieczywo"})
    await ala.post("/api/auth/logout")

    again = await login_as("ala")

    assert categories((await again.get("/api/list")).json())[0] == "Nabiał"


async def test_unpin_and_reset(household_with):
    (ala,) = await household_with("ala")
    await add(ala, *BREAD_DAIRY_HOUSEHOLD)
    await ala.put("/api/list/category-order/Chemia i higiena", json={"before": "Pieczywo"})
    await ala.put("/api/list/category-order/Nabiał", json={"before": "Chemia i higiena"})

    body = (await ala.delete("/api/list/category-order/Chemia i higiena")).json()
    assert categories(body) == ["Nabiał", "Pieczywo", "Chemia i higiena"]
    assert pinned(body) == ["Nabiał"]

    body = (await ala.delete("/api/list/category-order")).json()
    assert categories(body) == ["Pieczywo", "Nabiał", "Chemia i higiena"]
    assert pinned(body) == []


async def test_full_order_includes_empty_categories(household_with):
    (ala,) = await household_with("ala")
    await ala.put("/api/list/category-order/Inne", json={"before": "Warzywa i owoce"})

    body = (await ala.get("/api/list/category-order")).json()

    assert len(body) == 10
    assert body[0] == {"category": "Inne", "pinned": True}
    assert body[1] == {"category": "Warzywa i owoce", "pinned": False}


async def test_invalid_moves(household_with):
    (ala,) = await household_with("ala")

    response = await ala.put("/api/list/category-order/Nabiał", json={"after": "Nabiał"})
    assert response.status_code == 400
    assert (await ala.put("/api/list/category-order/Elektronika", json={})).status_code == 422
    assert (
        await ala.put("/api/list/category-order/Nabiał", json={"before": "Elektronika"})
    ).status_code == 422
    assert all(not e["pinned"] for e in (await ala.get("/api/list/category-order")).json())


async def test_category_order_requires_household(login_as):
    ala = await login_as("ala")

    assert (await ala.get("/api/list/category-order")).status_code == 409
    assert (await ala.put("/api/list/category-order/Nabiał", json={})).status_code == 409

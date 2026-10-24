"""Baza przepisów gospodarstwa (#46): API `/api/recipes` i dodawanie składników na listę."""

from kupto.recipes.library import ingredient_note

PANCAKES = {
    "name": "Naleśniki",
    "servings": "10 sztuk",
    "source_url": "https://przepisy.example/nalesniki",
    "instructions": "Zmiksuj składniki i smaż cienkie placki.",
    "ingredients": [
        {"name": "mąka pszenna", "note": "2 szklanki", "category": "Produkty suche"},
        {"name": "mleko", "amount": 0.5, "unit": "l", "category": "Nabiał"},
        {"name": "jajka", "amount": 2, "unit": "szt"},
        {"name": "sól", "note": "szczypta"},
    ],
}


def list_items(body):
    return {i["name"]: i for g in body["groups"] for i in g["items"]}


async def create(client, recipe=None, **changes):
    response = await client.post("/api/recipes", json={**(recipe or PANCAKES), **changes})
    assert response.status_code == 201, response.text
    return response.json()


async def test_recipe_is_shared_by_the_household(household_with):
    ala, ola = await household_with("ala", "ola")

    created = await create(ala)

    assert created["name"] == "Naleśniki"
    assert created["created_by"] == "ala"
    assert [i["name"] for i in created["ingredients"]] == ["mąka pszenna", "mleko", "jajka", "sól"]
    assert created["ingredients"][1] | {"id": 0} == {
        "id": 0,
        "name": "mleko",
        "amount": 0.5,
        "unit": "l",
        "note": None,
        "category": "Nabiał",
    }
    summaries = (await ola.get("/api/recipes")).json()
    assert [(s["id"], s["name"], s["servings"], s["ingredient_count"]) for s in summaries] == [
        (created["id"], "Naleśniki", "10 sztuk", 4)
    ]
    detail = (await ola.get(f"/api/recipes/{created['id']}")).json()
    assert detail == created


async def test_recipes_are_listed_alphabetically(household_with):
    (ala,) = await household_with("ala")
    for name in ("pierogi", "Bigos", "naleśniki"):
        await create(ala, name=name)

    names = [s["name"] for s in (await ala.get("/api/recipes")).json()]

    assert names == ["Bigos", "naleśniki", "pierogi"]


async def test_name_must_be_unique_in_household_ignoring_case(household_with):
    ala, ola = await household_with("ala", "ola")
    (ewa,) = await household_with("ewa", name="Inny dom")
    first = await create(ala)

    response = await ola.post("/api/recipes", json={**PANCAKES, "name": " naleśniki "})

    assert response.status_code == 409
    assert response.json()["code"] == "recipe_exists"
    # W innym gospodarstwie ta sama nazwa jest wolna.
    await create(ewa)
    # Zmiana innego przepisu na zajętą nazwę też jest odrzucana; zmiana na własną — nie.
    other = await create(ala, name="Placki")
    assert (
        await ala.put(f"/api/recipes/{other['id']}", json={**PANCAKES, "name": "NALEŚNIKI"})
    ).status_code == 409
    assert (
        await ala.put(f"/api/recipes/{first['id']}", json={**PANCAKES, "name": "naleśniki"})
    ).status_code == 200


async def test_update_replaces_fields_and_ingredients_keeping_id(household_with):
    ala, ola = await household_with("ala", "ola")
    created = await create(ala)

    response = await ola.put(
        f"/api/recipes/{created['id']}",
        json={
            "name": "Naleśniki na słodko",
            "servings": "",
            "source_url": None,
            "instructions": "  ",
            "ingredients": [
                {"name": "mleko", "amount": 1, "unit": "l"},
                {"name": "cukier", "note": "2 łyżki"},
            ],
        },
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["id"] == created["id"]
    assert updated["name"] == "Naleśniki na słodko"
    assert (updated["servings"], updated["source_url"], updated["instructions"]) == (
        None,
        None,
        None,
    )
    assert [(i["name"], i["amount"], i["note"]) for i in updated["ingredients"]] == [
        ("mleko", 1.0, None),
        ("cukier", None, "2 łyżki"),
    ]
    assert updated["created_by"] == "ala"
    assert updated["updated_at"] > created["updated_at"]
    assert (await ala.get(f"/api/recipes/{created['id']}")).json() == updated


async def test_delete_recipe(household_with):
    ala, ola = await household_with("ala", "ola")
    created = await create(ala)

    assert (await ola.delete(f"/api/recipes/{created['id']}")).status_code == 204

    assert (await ala.get("/api/recipes")).json() == []
    assert (await ala.get(f"/api/recipes/{created['id']}")).status_code == 404
    # Nazwa jest znów wolna.
    await create(ala)


async def test_other_household_cannot_access_recipe(household_with):
    (ala,) = await household_with("ala")
    (ewa,) = await household_with("ewa", name="Inny dom")
    recipe_id = (await create(ala))["id"]
    ingredient_id = (await ala.get(f"/api/recipes/{recipe_id}")).json()["ingredients"][0]["id"]

    assert (await ewa.get("/api/recipes")).json() == []
    assert (await ewa.get(f"/api/recipes/{recipe_id}")).status_code == 404
    assert (await ewa.put(f"/api/recipes/{recipe_id}", json=PANCAKES)).status_code == 404
    assert (await ewa.delete(f"/api/recipes/{recipe_id}")).status_code == 404
    response = await ewa.post(
        f"/api/recipes/{recipe_id}/to-list", json={"ingredient_ids": [ingredient_id]}
    )
    assert response.status_code == 404
    assert list_items((await ewa.get("/api/list")).json()) == {}
    assert (await ala.get(f"/api/recipes/{recipe_id}")).json()["name"] == "Naleśniki"


async def test_validation(household_with):
    (ala,) = await household_with("ala")

    for invalid in (
        {"name": "  "},
        {"ingredients": []},
        {"ingredients": [{"name": "mleko", "amount": 0}]},
        {"ingredients": [{"name": "mleko", "unit": "szklanka"}]},
        {"source_url": "javascript:alert(1)"},
        {"source_url": "ftp://przepisy.example/x"},
        {"instructions": "x" * 8001},
        {"ingredients": [{"name": f"składnik {i}"} for i in range(61)]},
    ):
        response = await ala.post("/api/recipes", json={**PANCAKES, **invalid})
        assert response.status_code == 422, invalid

    assert (await ala.get("/api/recipes")).json() == []


async def test_recipes_require_login_and_household(client, login_as):
    assert (await client.get("/api/recipes")).status_code == 401
    lonely = await login_as("ala")
    response = await lonely.post("/api/recipes", json=PANCAKES)
    assert response.status_code == 409
    assert response.json()["code"] == "no_household"


async def test_selected_ingredients_are_added_with_dish_note(household_with):
    ala, ola = await household_with("ala", "ola")
    recipe = await create(ola)
    flour, milk, eggs, salt = (i["id"] for i in recipe["ingredients"])
    await ala.post("/api/list/needs", json={"name": "Mleko", "category": "Nabiał"})

    response = await ala.post(
        f"/api/recipes/{recipe['id']}/to-list", json={"ingredient_ids": [milk, flour]}
    )

    assert response.status_code == 200
    # Kolejność z przepisu; mleko było już na liście.
    assert response.json() == {
        "added": [
            {"name": "mąka pszenna", "category": "Produkty suche", "already_on_list": False},
            {"name": "Mleko", "category": "Nabiał", "already_on_list": True},
        ]
    }
    items = list_items((await ola.get("/api/list")).json())
    assert set(items) == {"mąka pszenna", "Mleko"}
    flour_need = items["mąka pszenna"]["needs"][0]
    assert (flour_need["name"], flour_need["amount"], flour_need["note"]) == (
        "ala",
        None,
        "na: Naleśniki (2 szklanki)",
    )
    milk_needs = items["Mleko"]["needs"]
    assert [(n["name"], n["amount"], n["unit"], n["note"]) for n in milk_needs] == [
        ("ala", None, None, None),
        ("ala", 0.5, "l", "na: Naleśniki"),
    ]


async def test_ingredient_from_other_recipe_is_rejected(household_with):
    (ala,) = await household_with("ala")
    pancakes = await create(ala)
    other = await create(ala, name="Placki")

    response = await ala.post(
        f"/api/recipes/{pancakes['id']}/to-list",
        json={"ingredient_ids": [pancakes["ingredients"][0]["id"], other["ingredients"][0]["id"]]},
    )

    assert response.status_code == 404
    assert list_items((await ala.get("/api/list")).json()) == {}
    assert (
        await ala.post(f"/api/recipes/{pancakes['id']}/to-list", json={"ingredient_ids": []})
    ).status_code == 422


def test_ingredient_note_is_trimmed_to_need_note_limit():
    assert ingredient_note("Naleśniki", None) == "na: Naleśniki"
    assert ingredient_note("Naleśniki", "2 szklanki") == "na: Naleśniki (2 szklanki)"
    long = ingredient_note("x" * 100, "y" * 200)
    assert len(long) == 200 and long.endswith("…")

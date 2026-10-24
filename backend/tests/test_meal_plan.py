"""Plan obiadów gospodarstwa (#44): API `/api/meal-plan` pod kalendarz (#47)."""

from tests.test_household_recipes import PANCAKES, create

URL = "/api/meal-plan"
WEEK = {"from": "2026-10-26", "to": "2026-11-01"}


async def set_day(client, day, **payload):
    response = await client.put(f"{URL}/{day}", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


async def plan(client, **params):
    response = await client.get(URL, params=params or WEEK)
    assert response.status_code == 200, response.text
    return [(e["day"], e["name"], e["recipe_id"]) for e in response.json()]


async def test_plan_is_shared_by_the_household(household_with):
    ala, ola = await household_with("ala", "ola")
    recipe = await create(ala)

    entry = await set_day(ala, "2026-10-27", recipe_id=recipe["id"])

    # Nazwa dania domyślnie z przepisu.
    assert entry | {"id": 0, "updated_at": ""} == {
        "id": 0,
        "day": "2026-10-27",
        "name": "Naleśniki",
        "recipe_id": recipe["id"],
        "planned_by": "ala",
        "updated_at": "",
    }
    (shown,) = (await ola.get(URL, params=WEEK)).json()
    assert shown == entry


async def test_setting_a_day_replaces_its_dish(household_with):
    ala, ola = await household_with("ala", "ola")
    recipe = await create(ala)
    first = await set_day(ala, "2026-10-27", recipe_id=recipe["id"])

    second = await set_day(ola, "2026-10-27", name="  Pierogi  ")

    assert second["id"] == first["id"]
    assert (second["name"], second["recipe_id"], second["planned_by"]) == ("Pierogi", None, "ola")
    assert await plan(ala) == [("2026-10-27", "Pierogi", None)]


async def test_own_name_is_kept_with_recipe(household_with):
    (ala,) = await household_with("ala")
    recipe = await create(ala)

    entry = await set_day(ala, "2026-10-27", name="Naleśniki z serem", recipe_id=recipe["id"])

    assert (entry["name"], entry["recipe_id"]) == ("Naleśniki z serem", recipe["id"])


async def test_range_is_inclusive_sorted_and_skips_empty_days(household_with):
    (ala,) = await household_with("ala")
    for day, name in (("2026-11-03", "Bigos"), ("2026-10-28", "Pierogi"), ("2026-10-26", "Zupa")):
        await set_day(ala, day, name=name)

    assert await plan(ala) == [("2026-10-26", "Zupa", None), ("2026-10-28", "Pierogi", None)]
    assert await plan(ala, **{"from": "2026-11-01", "to": "2026-11-03"}) == [
        ("2026-11-03", "Bigos", None)
    ]


async def test_invalid_range_is_rejected(household_with):
    (ala,) = await household_with("ala")

    reversed_range = await ala.get(URL, params={"from": "2026-11-01", "to": "2026-10-26"})
    too_long = await ala.get(URL, params={"from": "2026-10-01", "to": "2026-12-02"})
    longest = await ala.get(URL, params={"from": "2026-10-01", "to": "2026-12-01"})  # 62 dni
    missing = await ala.get(URL, params={"from": "2026-10-01"})

    assert (reversed_range.status_code, too_long.status_code) == (400, 400)
    assert longest.status_code == 200
    assert missing.status_code == 422


async def test_day_needs_name_or_recipe(household_with):
    (ala,) = await household_with("ala")

    assert (await ala.put(f"{URL}/2026-10-27", json={"name": "  "})).status_code == 422
    assert (await ala.put(f"{URL}/2026-10-27", json={})).status_code == 422
    assert (await ala.put(f"{URL}/27-10-2026", json={"name": "Zupa"})).status_code == 422
    assert await plan(ala) == []


async def test_deleting_a_day_keeps_the_rest(household_with):
    (ala,) = await household_with("ala")
    await set_day(ala, "2026-10-27", name="Zupa")
    await set_day(ala, "2026-10-28", name="Pierogi")

    assert (await ala.delete(f"{URL}/2026-10-28")).status_code == 204

    assert await plan(ala) == [("2026-10-27", "Zupa", None)]
    assert (await ala.delete(f"{URL}/2026-10-28")).status_code == 404


async def test_deleted_recipe_leaves_the_dish_in_the_plan(household_with):
    (ala,) = await household_with("ala")
    recipe = await create(ala)
    await set_day(ala, "2026-10-27", recipe_id=recipe["id"])

    assert (await ala.delete(f"/api/recipes/{recipe['id']}")).status_code == 204

    assert await plan(ala) == [("2026-10-27", "Naleśniki", None)]


async def test_plan_is_isolated_between_households(household_with):
    (ala,) = await household_with("ala")
    (ewa,) = await household_with("ewa", name="Sąsiedzi")
    ala_recipe = await create(ala)
    ewa_recipe = await create(ewa, PANCAKES, name="Bigos")
    await set_day(ala, "2026-10-27", name="Zupa")

    assert await plan(ewa) == []
    foreign = await ewa.put(f"{URL}/2026-10-27", json={"recipe_id": ala_recipe["id"]})
    assert foreign.status_code == 404
    assert (await ewa.delete(f"{URL}/2026-10-27")).status_code == 404
    # Ewa planuje ten sam dzień niezależnie od ali.
    await set_day(ewa, "2026-10-27", recipe_id=ewa_recipe["id"])
    assert await plan(ala) == [("2026-10-27", "Zupa", None)]
    assert await plan(ewa) == [("2026-10-27", "Bigos", ewa_recipe["id"])]


async def test_plan_requires_household(login_as):
    nobody = await login_as("ala")

    assert (await nobody.get(URL, params=WEEK)).status_code == 409

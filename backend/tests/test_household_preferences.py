"""Preferencje gospodarstwa (#45): API `/api/households/me/preferences` i postać dla modelu."""

from kupto.households.preferences import Preferences, PreferencesIn, for_model

URL = "/api/households/me/preferences"

EMPTY = {
    "people": None,
    "diets": [],
    "excluded": [],
    "disliked": [],
    "max_cooking_minutes": None,
    "notes": None,
    "updated_by": None,
    "updated_at": None,
}

VEGETARIAN = {
    "people": 4,
    "diets": ["wegetariańska"],
    "excluded": ["orzechy"],
    "disliked": ["seler"],
    "max_cooking_minutes": 45,
    "notes": "w tygodniu tanio",
}


async def test_household_without_preferences_has_empty_fields(household_with):
    (ala,) = await household_with("ala")

    response = await ala.get(URL)

    assert response.status_code == 200
    assert response.json() == EMPTY


async def test_preferences_are_shared_by_the_household(household_with):
    ala, ola = await household_with("ala", "ola")

    saved = await ola.put(URL, json=VEGETARIAN)

    assert saved.status_code == 200, saved.text
    body = (await ala.get(URL)).json()
    assert body | {"updated_at": None} == {**VEGETARIAN, "updated_by": "ola", "updated_at": None}
    assert body["updated_at"] is not None


async def test_put_replaces_all_preferences(household_with):
    (ala,) = await household_with("ala")
    await ala.put(URL, json=VEGETARIAN)

    response = await ala.put(URL, json={"excluded": ["gluten"]})

    assert response.json() | {"updated_at": None} == {
        **EMPTY,
        "excluded": ["gluten"],
        "updated_by": "ala",
    }


async def test_lists_are_trimmed_and_deduplicated(household_with):
    (ala,) = await household_with("ala")

    response = await ala.put(
        URL, json={"excluded": [" orzechy", "Orzechy", "", "  ", "owoce  morza"], "notes": "  "}
    )

    assert response.json()["excluded"] == ["orzechy", "owoce morza"]
    assert response.json()["notes"] is None


async def test_invalid_preferences_are_rejected_without_change(household_with):
    (ala,) = await household_with("ala")
    await ala.put(URL, json=VEGETARIAN)

    for invalid in (
        {"people": 0},
        {"max_cooking_minutes": 1000},
        {"diets": ["x" * 51]},
        {"disliked": [f"p{i}" for i in range(21)]},
        {"notes": "x" * 301},
    ):
        response = await ala.put(URL, json=invalid)
        assert response.status_code == 422, invalid

    assert (await ala.get(URL)).json()["people"] == 4


async def test_other_household_has_its_own_preferences(household_with):
    (ala,) = await household_with("ala")
    (ewa,) = await household_with("ewa", name="Inny dom")
    await ala.put(URL, json=VEGETARIAN)

    assert (await ewa.get(URL)).json() == EMPTY

    await ewa.put(URL, json={"people": 2})
    assert (await ala.get(URL)).json()["people"] == 4


async def test_preferences_require_a_household(login_as):
    lonely = await login_as("ala")

    response = await lonely.get(URL)

    assert response.status_code == 409
    assert response.json()["code"] == "no_household"


def test_model_gets_only_set_fields():
    assert for_model(Preferences()) == {}
    assert for_model(Preferences(people=2, excluded=["orzechy"], updated_by="ala")) == {
        "people": 2,
        "excluded": ["orzechy"],
    }


def test_input_normalization_keeps_order():
    data = PreferencesIn(diets=["bez glutenu", " wegańska ", "BEZ GLUTENU"])

    assert data.diets == ["bez glutenu", "wegańska"]

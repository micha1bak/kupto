import json

import pytest

from kupto.chat.tools import (
    TOOL_DEFINITIONS,
    ToolContext,
    clear_pending_action,
    execute_tool,
)
from kupto.households import preferences
from kupto.households import service as households
from kupto.models import User


@pytest.fixture
async def home(session):
    ala, ola, ewa = (User(login=n, password_hash="x") for n in ("ala", "ola", "ewa"))
    session.add_all([ala, ola, ewa])
    await session.commit()
    household = await households.create_household(session, ala, "Dom")
    await households.add_member(session, ala, household, "ola")
    other = await households.create_household(session, ewa, "Inny dom")
    return {
        "ala": ToolContext(session, household, ala),
        "ola": ToolContext(session, household, ola),
        "ewa": ToolContext(session, other, ewa),
    }


async def call(ctx, name, **args):
    return await execute_tool(ctx, name, json.dumps(args))


def need(name, amount=None, unit=None, note=None, category="Inne"):
    return {"name": name, "amount": amount, "unit": unit, "note": note, "category": category}


def test_tool_schemas_are_strict():
    def check(schema):
        if schema.get("type") == "object":
            assert schema["additionalProperties"] is False
            assert set(schema["required"]) == set(schema["properties"])
            for prop in schema["properties"].values():
                check(prop)
        if schema.get("type") == "array":
            check(schema["items"])

    for tool in TOOL_DEFINITIONS:
        assert tool["strict"] is True
        check(tool["parameters"])


async def test_add_needs_then_get_list(home):
    result = await call(
        home["ala"], "add_needs", items=[need("mleko", 2, "l", "bez laktozy", "Nabiał")]
    )
    assert result.list_changed
    assert result.output == {
        "added": [{"name": "mleko", "category": "Nabiał", "already_on_list": False}]
    }

    snapshot = (await call(home["ola"], "get_list")).output
    (item,) = snapshot["items"]
    assert (item["name"], item["quantities"]) == ("mleko", ["2 l"])
    assert item["needs"][0]["requested_by"] == "ala"
    assert item["needs"][0]["mine"] is False


async def test_snapshot_formats_round_amounts_plainly(home):
    await call(
        home["ala"], "add_needs", items=[need("jajka", 10, "szt"), need("drożdże", 100, "g")]
    )

    items = {i["name"]: i for i in (await call(home["ala"], "get_list")).output["items"]}

    assert items["jajka"]["quantities"] == ["10 szt"]
    assert items["drożdże"]["quantities"] == ["100 g"]


async def test_mark_bought_with_unknown_id_changes_nothing(home):
    await call(home["ala"], "add_needs", items=[need("mleko")])
    item_id = (await call(home["ala"], "get_list")).output["items"][0]["item_id"]

    result = await call(home["ala"], "mark_bought", item_ids=[item_id, 999999])

    assert "error" in result.output
    assert (await call(home["ala"], "get_list")).output["items"][0]["bought"] is False


async def test_merge_is_reported(home):
    await call(home["ala"], "add_needs", items=[need("mleko")])

    result = await call(home["ola"], "add_needs", items=[need("Mleko")])

    assert result.output["added"][0]["already_on_list"] is True


async def test_invalid_item_returns_error_without_changes(home):
    result = await call(home["ala"], "add_needs", items=[need("x" * 101)])

    assert "error" in result.output
    assert not result.list_changed
    assert (await call(home["ala"], "get_list")).output["items"] == []


async def test_unknown_tool_and_bad_arguments(home):
    assert "error" in (await execute_tool(home["ala"], "drop_database", "{}")).output
    assert "error" in (await execute_tool(home["ala"], "remove_item", "{nie json")).output
    assert "error" in (await call(home["ala"], "remove_item", wrong=1)).output


async def test_cannot_touch_other_household(home):
    await call(home["ala"], "add_needs", items=[need("mleko")])
    item = (await call(home["ala"], "get_list")).output["items"][0]

    for name, args in [
        ("remove_item", {"item_id": item["item_id"]}),
        ("mark_bought", {"item_ids": [item["item_id"]]}),
        ("withdraw_need", {"need_id": item["needs"][0]["need_id"]}),
    ]:
        result = await call(home["ewa"], name, **args)
        assert "error" in result.output and not result.list_changed

    assert (await call(home["ewa"], "get_list")).output["items"] == []
    (unchanged,) = (await call(home["ala"], "get_list")).output["items"]
    assert unchanged["bought"] is False


async def test_cannot_change_someone_elses_need(home):
    await call(home["ala"], "add_needs", items=[need("mleko")])
    need_id = (await call(home["ola"], "get_list")).output["items"][0]["needs"][0]["need_id"]

    update = await call(home["ola"], "update_need", need_id=need_id, amount=5, unit=None, note=None)
    withdraw = await call(home["ola"], "withdraw_need", need_id=need_id)

    assert "error" in update.output and "error" in withdraw.output


async def test_update_and_withdraw_own_need(home):
    await call(home["ala"], "add_needs", items=[need("mleko", 1, "l")])
    need_id = (await call(home["ala"], "get_list")).output["items"][0]["needs"][0]["need_id"]

    await call(home["ala"], "update_need", need_id=need_id, amount=3, unit=None, note=None)
    assert (await call(home["ala"], "get_list")).output["items"][0]["quantities"] == ["3 l"]

    await call(home["ala"], "withdraw_need", need_id=need_id)
    assert (await call(home["ala"], "get_list")).output["items"] == []


async def test_mark_bought_and_remove(home):
    await call(home["ala"], "add_needs", items=[need("mleko"), need("chleb")])
    items = {i["name"]: i["item_id"] for i in (await call(home["ala"], "get_list")).output["items"]}

    result = await call(home["ola"], "mark_bought", item_ids=[items["mleko"], items["chleb"]])
    assert sorted(result.output["marked_bought"]) == ["chleb", "mleko"]

    await call(home["ola"], "remove_item", item_id=items["chleb"])
    (milk,) = (await call(home["ala"], "get_list")).output["items"]
    assert milk["bought"] is True


async def start_turn(ctx):
    ctx.pending_action = await clear_pending_action(ctx.session, ctx.user)


async def prepare_bought_and_unbought(ctx):
    await call(ctx, "add_needs", items=[need("mleko"), need("chleb")])
    items = {i["name"]: i["item_id"] for i in (await call(ctx, "get_list")).output["items"]}
    await call(ctx, "mark_bought", item_ids=[items["mleko"]])


async def test_confirm_without_request_does_nothing(home, purchase_history):
    ctx = home["ala"]
    await prepare_bought_and_unbought(ctx)
    await start_turn(ctx)

    result = await call(ctx, "confirm_finish_shopping")

    assert "error" in result.output
    assert len((await call(ctx, "get_list")).output["items"]) == 2
    assert await purchase_history() == []


async def test_confirm_in_same_turn_as_request_does_nothing(home):
    ctx = home["ala"]
    await prepare_bought_and_unbought(ctx)
    await start_turn(ctx)

    request = await call(ctx, "request_finish_shopping")
    confirm = await call(ctx, "confirm_finish_shopping")

    assert request.output["bought_items_to_archive"] == ["mleko"]
    assert "error" in confirm.output


async def test_confirm_in_next_turn_finishes_shopping(home, purchase_history):
    ctx = home["ala"]
    await prepare_bought_and_unbought(ctx)
    await start_turn(ctx)
    await call(ctx, "request_finish_shopping")

    await start_turn(ctx)
    result = await call(ctx, "confirm_finish_shopping")

    assert result.output == {"status": "finished", "archived_items": 1}
    assert result.list_changed
    assert [i["name"] for i in (await call(ctx, "get_list")).output["items"]] == ["chleb"]
    (trip,) = await purchase_history(ctx.household.id)
    assert trip.finished_by_id == ctx.user.id
    assert [(i.name, i.bought_by_id) for i in trip.items] == [("mleko", ctx.user.id)]


async def test_any_other_message_cancels_pending_confirmation(home, purchase_history):
    ctx = home["ala"]
    await prepare_bought_and_unbought(ctx)
    await start_turn(ctx)
    await call(ctx, "request_finish_shopping")

    await start_turn(ctx)  # użytkownik napisał coś innego, model nie potwierdził
    await start_turn(ctx)
    result = await call(ctx, "confirm_finish_shopping")

    assert "error" in result.output
    assert len((await call(ctx, "get_list")).output["items"]) == 2
    assert await purchase_history() == []


async def test_start_shopping_is_visible_to_household_and_keeps_list(home):
    await call(home["ala"], "add_needs", items=[need("mleko")])

    result = await call(home["ala"], "start_shopping")

    assert result.list_changed
    assert result.output == {
        "status": "shopping",
        "already_shopping": False,
        "expires_in_hours": 3,
        "others_shopping": [],
    }
    snapshot = (await call(home["ola"], "get_list")).output
    assert snapshot["shopping_now"] == ["ala"]
    assert [i["name"] for i in snapshot["items"]] == ["mleko"]
    assert (await call(home["ewa"], "get_list")).output["shopping_now"] == []


async def test_start_shopping_reports_existing_status_and_others(home):
    await call(home["ola"], "start_shopping")
    await call(home["ala"], "start_shopping")

    result = await call(home["ala"], "start_shopping")

    assert result.output["already_shopping"] is True
    assert result.output["others_shopping"] == ["ola"]


async def test_stop_shopping(home):
    await call(home["ala"], "start_shopping")

    stopped = await call(home["ala"], "stop_shopping")
    again = await call(home["ala"], "stop_shopping")

    assert (stopped.output, stopped.list_changed) == ({"status": "stopped"}, True)
    assert again.output == {"status": "was_not_shopping"}
    assert (await call(home["ala"], "get_list")).output["shopping_now"] == []


async def test_confirmed_finish_shopping_clears_status(home):
    ctx = home["ala"]
    await prepare_bought_and_unbought(ctx)
    await call(ctx, "start_shopping")
    await start_turn(ctx)
    await call(ctx, "request_finish_shopping")
    assert (await call(ctx, "get_list")).output["shopping_now"] == ["ala"]

    await start_turn(ctx)
    await call(ctx, "confirm_finish_shopping")

    assert (await call(ctx, "get_list")).output["shopping_now"] == []


async def test_get_usual_missing_is_read_only(home):
    from datetime import timedelta

    from kupto.db import utcnow
    from kupto.models import Category, PurchasedItem, PurchasedNeed, ShoppingTrip, Unit

    ctx = home["ala"]
    for days in (28, 21, 14, 7):
        finished_at = utcnow() - timedelta(days=days)
        milk = PurchasedItem(
            name="mleko",
            normalized_name="mleko",
            category=Category("Nabiał"),
            bought_at=finished_at,
            needs=[PurchasedNeed(amount=2, unit=Unit("l"), requested_at=finished_at)],
        )
        ctx.session.add(
            ShoppingTrip(household_id=ctx.household.id, finished_at=finished_at, items=[milk])
        )
    await ctx.session.commit()

    result = await call(ctx, "get_usual_missing")
    other = await call(home["ewa"], "get_usual_missing")

    assert result.list_changed is False
    (milk,) = result.output["usual_missing"]
    assert milk["name"] == "mleko"
    assert (milk["typical_amount"], milk["unit"]) == (2.0, "l")
    assert (milk["bought_times"], milk["every_days"]) == (4, 7.0)
    assert milk["days_since_last"] == 7.0
    assert other.output == {"usual_missing": []}
    assert (await call(ctx, "get_list")).output["items"] == []


async def test_fetch_recipe_is_read_only_and_returns_page_result(home, monkeypatch):
    requested = []

    async def fake_recipe_from_url(url):
        requested.append(url)
        return {"source": "schema.org", "url": url, "name": "Naleśniki", "ingredients": ["mąka"]}

    monkeypatch.setattr("kupto.chat.tools.recipe_from_url", fake_recipe_from_url)
    ctx = home["ala"]

    result = await call(ctx, "fetch_recipe", url="https://przepisy.example/nalesniki")

    assert requested == ["https://przepisy.example/nalesniki"]
    assert result.list_changed is False
    assert result.output["ingredients"] == ["mąka"]
    assert (await call(ctx, "get_list")).output["items"] == []


async def test_fetch_recipe_blocks_private_address_without_mocks(home):
    result = await call(home["ala"], "fetch_recipe", url="http://169.254.169.254/latest/")

    assert result.list_changed is False
    assert "sieci prywatnej" in result.output["error"]


def ingredient(name, amount=None, unit=None, note=None, category="Inne"):
    return {"name": name, "amount": amount, "unit": unit, "note": note, "category": category}


PANCAKES = {
    "name": "Naleśniki",
    "servings": "10 sztuk",
    "source_url": None,
    "instructions": "Zmiksuj i smaż.",
    "ingredients": [
        ingredient("mąka pszenna", note="2 szklanki", category="Produkty suche"),
        ingredient("mleko", 0.5, "l", category="Nabiał"),
        ingredient("sól", note="szczypta"),
    ],
}


async def save_recipe(ctx, recipe):
    return await execute_tool(ctx, "save_recipe", json.dumps(recipe))


async def test_saved_recipe_is_shared_and_does_not_change_list(home):
    result = await save_recipe(home["ala"], PANCAKES)

    assert result.list_changed is False
    saved = result.output["saved"]
    assert saved["name"] == "Naleśniki"
    assert saved["ingredients"] == ["mąka pszenna", "mleko", "sól"]
    assert (await call(home["ala"], "get_list")).output["items"] == []

    listed = (await call(home["ola"], "list_recipes")).output
    assert listed == {
        "recipes": [{"recipe_id": saved["recipe_id"], "name": "Naleśniki", "servings": "10 sztuk"}]
    }
    recipe = (await call(home["ola"], "get_recipe", recipe_id=saved["recipe_id"])).output
    assert recipe["ingredients"] == [
        {
            "name": "mąka pszenna",
            "amount": None,
            "unit": None,
            "note": "2 szklanki",
            "category": "Produkty suche",
        },
        {"name": "mleko", "amount": 0.5, "unit": "l", "note": None, "category": "Nabiał"},
        {"name": "sól", "amount": None, "unit": None, "note": "szczypta", "category": "Inne"},
    ]
    assert recipe["instructions"] == "Zmiksuj i smaż."


async def test_recipe_tools_respect_household_and_report_errors(home):
    saved = (await save_recipe(home["ala"], PANCAKES)).output["saved"]

    assert (await call(home["ewa"], "list_recipes")).output == {"recipes": []}
    foreign = await call(home["ewa"], "get_recipe", recipe_id=saved["recipe_id"])
    assert foreign.output == {"error": "Nie ma takiego przepisu."}

    duplicate = await save_recipe(home["ola"], {**PANCAKES, "name": "NALEŚNIKI"})
    assert "już zapisany" in duplicate.output["error"]
    invalid = await save_recipe(home["ala"], {**PANCAKES, "ingredients": []})
    assert invalid.output["error"].startswith("Nieprawidłowe dane")
    assert len((await call(home["ala"], "list_recipes")).output["recipes"]) == 1


def preferences_args(**changes):
    names = ("people", "diets", "excluded", "disliked", "max_cooking_minutes", "notes")
    return dict.fromkeys(names) | changes


async def test_update_preferences_keeps_unchanged_fields_and_is_shared(home):
    first = await call(
        home["ala"], "update_preferences", **preferences_args(people=4, excluded=["orzechy"])
    )
    assert first.output == {"preferences": {"people": 4, "excluded": ["orzechy"]}}

    result = await call(
        home["ola"], "update_preferences", **preferences_args(excluded=["orzechy", "seler"])
    )

    # Zmiana preferencji nie dotyczy listy zakupów.
    assert not result.list_changed
    assert result.output == {"preferences": {"people": 4, "excluded": ["orzechy", "seler"]}}
    saved = await preferences.load(home["ala"].session, home["ala"].household)
    assert saved.updated_by == "ola"
    other = await preferences.load(home["ewa"].session, home["ewa"].household)
    assert other == preferences.Preferences()


async def test_update_preferences_rejects_invalid_values_without_change(home):
    await call(home["ala"], "update_preferences", **preferences_args(people=4))

    result = await call(home["ala"], "update_preferences", **preferences_args(people=0))

    assert "error" in result.output
    saved = await preferences.load(home["ala"].session, home["ala"].household)
    assert saved.people == 4

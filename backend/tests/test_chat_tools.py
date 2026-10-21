import json

import pytest

from kupto.chat.tools import (
    TOOL_DEFINITIONS,
    ToolContext,
    clear_pending_action,
    execute_tool,
)
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


async def test_confirm_without_request_does_nothing(home):
    ctx = home["ala"]
    await prepare_bought_and_unbought(ctx)
    await start_turn(ctx)

    result = await call(ctx, "confirm_finish_shopping")

    assert "error" in result.output
    assert len((await call(ctx, "get_list")).output["items"]) == 2


async def test_confirm_in_same_turn_as_request_does_nothing(home):
    ctx = home["ala"]
    await prepare_bought_and_unbought(ctx)
    await start_turn(ctx)

    request = await call(ctx, "request_finish_shopping")
    confirm = await call(ctx, "confirm_finish_shopping")

    assert request.output["bought_items_to_remove"] == ["mleko"]
    assert "error" in confirm.output


async def test_confirm_in_next_turn_finishes_shopping(home):
    ctx = home["ala"]
    await prepare_bought_and_unbought(ctx)
    await start_turn(ctx)
    await call(ctx, "request_finish_shopping")

    await start_turn(ctx)
    result = await call(ctx, "confirm_finish_shopping")

    assert result.output == {"status": "finished", "removed_items": 1}
    assert result.list_changed
    assert [i["name"] for i in (await call(ctx, "get_list")).output["items"]] == ["chleb"]


async def test_any_other_message_cancels_pending_confirmation(home):
    ctx = home["ala"]
    await prepare_bought_and_unbought(ctx)
    await start_turn(ctx)
    await call(ctx, "request_finish_shopping")

    await start_turn(ctx)  # użytkownik napisał coś innego, model nie potwierdził
    await start_turn(ctx)
    result = await call(ctx, "confirm_finish_shopping")

    assert "error" in result.output
    assert len((await call(ctx, "get_list")).output["items"]) == 2

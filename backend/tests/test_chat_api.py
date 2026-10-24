import json
import logging
from datetime import date, timedelta

from sqlalchemy import update

from kupto.chat.llm import LLMUnavailable, TextDelta, ToolCall, Usage
from kupto.chat.tools import TOOL_DEFINITIONS
from kupto.meal_plan import service as meal_plan
from kupto.models import ChatMessage


def parse_sse(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


async def send(client, content: str):
    response = await client.post("/api/chat/messages", json={"content": content})
    return response, parse_sse(response.text) if response.status_code == 200 else []


def add_needs_call(*items, call_id="call_1"):
    payload = [
        {"name": n, "amount": a, "unit": u, "note": None, "category": c} for n, a, u, c in items
    ]
    return ToolCall(call_id, "add_needs", json.dumps({"items": payload}))


def list_items(body):
    return {i["name"]: i for g in body["groups"] for i in g["items"]}


async def test_reply_is_streamed_and_ends_with_done(household_with, fake_llm):
    (ala,) = await household_with("ala")
    fake_llm.rounds.append([TextDelta("Cześć"), TextDelta("! W czym pomóc?")])

    response, events = await send(ala, "Hej")

    assert response.headers["content-type"].startswith("text/event-stream")
    assert events == [
        ("delta", {"text": "Cześć"}),
        ("delta", {"text": "! W czym pomóc?"}),
        ("done", {}),
    ]


async def test_products_are_added_as_authors_needs(household_with, fake_llm):
    ala, ola = await household_with("ala", "ola")
    fake_llm.rounds += [
        [
            add_needs_call(
                ("mleko", 2, "szt", "Nabiał"),
                ("chleb", None, None, "Pieczywo"),
                ("płyn do naczyń", None, None, "Chemia i higiena"),
            )
        ],
        [TextDelta("Dodałem mleko, chleb i płyn do naczyń.")],
    ]

    _, events = await send(ala, "kup 2 mleka, chleb i płyn do naczyń")

    assert ("list_changed", {}) in events
    items = list_items((await ola.get("/api/list")).json())
    assert {n: i["category"] for n, i in items.items()} == {
        "mleko": "Nabiał",
        "chleb": "Pieczywo",
        "płyn do naczyń": "Chemia i higiena",
    }
    assert all(i["needs"][0]["login"] == "ala" for i in items.values())
    # wynik narzędzia wraca do modelu w drugiej rundzie
    second_input = fake_llm.calls[1]["input"]
    assert second_input[-2]["type"] == "function_call"
    assert second_input[-1]["type"] == "function_call_output"
    assert json.loads(second_input[-1]["output"])["added"][0]["name"] == "mleko"


async def test_merge_with_existing_item_is_reported_to_model(household_with, fake_llm):
    ala, ola = await household_with("ala", "ola")
    await ala.post("/api/list/needs", json={"name": "mleko", "category": "Nabiał"})
    fake_llm.rounds += [
        [add_needs_call(("mleko", 1, "l", "Nabiał"))],
        [TextDelta("Mleko już było.")],
    ]

    await send(ola, "skończyło się mleko")

    output = json.loads(fake_llm.calls[1]["input"][-1]["output"])
    assert output["added"][0]["already_on_list"] is True
    assert [
        n["login"] for n in list_items((await ala.get("/api/list")).json())["mleko"]["needs"]
    ] == [
        "ala",
        "ola",
    ]


async def test_model_receives_instructions_list_and_history(household_with, fake_llm):
    (ala,) = await household_with("ala")
    await ala.post("/api/list/needs", json={"name": "chleb"})
    fake_llm.rounds += [[TextDelta("Pierwsza odpowiedź")], [TextDelta("Druga odpowiedź")]]

    await send(ala, "pierwsza")
    await send(ala, "druga")

    call = fake_llm.calls[1]
    assert '"name": "chleb"' in call["instructions"]
    assert call["input"] == [
        {"role": "user", "content": "pierwsza"},
        {"role": "assistant", "content": "Pierwsza odpowiedź"},
        {"role": "user", "content": "druga"},
    ]
    assert call["tools"] == TOOL_DEFINITIONS


async def test_tool_rounds_are_limited(household_with, fake_llm, settings):
    (ala,) = await household_with("ala")
    rounds = settings.chat_max_tool_rounds
    fake_llm.rounds += [[ToolCall(f"c{i}", "get_list", "{}")] for i in range(rounds)]
    fake_llm.rounds.append([TextDelta("Koniec")])

    _, events = await send(ala, "co mamy?")

    assert len(fake_llm.calls) == rounds + 1
    assert fake_llm.calls[-1]["tools"] == []
    assert events[-2:] == [("delta", {"text": "Koniec"}), ("done", {})]


async def test_text_from_tool_round_is_kept_and_separated(household_with, fake_llm):
    (ala,) = await household_with("ala")
    fake_llm.rounds += [
        [TextDelta("Dodaję mleko."), add_needs_call(("mleko", None, None, "Nabiał"))],
        [TextDelta("Gotowe.")],
    ]

    _, events = await send(ala, "kup mleko")

    texts = [data["text"] for name, data in events if name == "delta"]
    assert "".join(texts) == "Dodaję mleko.\n\nGotowe."
    second_input = fake_llm.calls[1]["input"]
    assert {"role": "assistant", "content": "Dodaję mleko."} in second_input
    history = (await ala.get("/api/chat/messages")).json()
    assert history[-1]["content"] == "Dodaję mleko.\n\nGotowe."


async def test_model_error_keeps_changes_made_before_it(household_with, fake_llm):
    (ala,) = await household_with("ala")
    fake_llm.rounds += [[add_needs_call(("chleb", None, None, "Pieczywo"))], LLMUnavailable("boom")]

    _, events = await send(ala, "kup chleb")

    assert events[-2][0] == "error"
    assert "chwilowo niedostępny" in events[-2][1]["message"]
    assert events[-1] == ("done", {})
    assert "chleb" in list_items((await ala.get("/api/list")).json())


def usage_records(caplog):
    return [r for r in caplog.records if getattr(r, "event", None) == "llm_usage"]


async def test_token_usage_is_logged_without_content(household_with, fake_llm, settings, caplog):
    caplog.set_level(logging.INFO, logger="kupto")
    (ala,) = await household_with("ala")
    fake_llm.rounds += [
        [add_needs_call(("mleko", None, None, "Nabiał")), Usage(100, 20, cached_tokens=50)],
        [TextDelta("Dodałem mleko."), Usage(150, 10, reasoning_tokens=4)],
    ]
    user = (await ala.get("/api/users/me")).json()
    household = (await ala.get("/api/households/me")).json()

    await send(ala, "kup mleko tajne")

    (record,) = usage_records(caplog)
    assert record.outcome == "ok"
    assert record.model == settings.openai_model
    assert (record.user_id, record.household_id) == (user["id"], household["id"])
    assert (record.input_tokens, record.output_tokens) == (250, 30)
    assert (record.cached_tokens, record.reasoning_tokens) == (50, 4)
    assert (record.model_calls, record.tool_rounds) == (2, 1)
    assert record.tool_calls == ["add_needs"]
    assert record.duration_ms >= 0
    logged = caplog.text + repr([vars(r) for r in caplog.records])
    assert "tajne" not in logged
    assert "Dodałem" not in logged


async def test_token_usage_is_logged_when_model_fails(household_with, fake_llm, caplog):
    caplog.set_level(logging.INFO, logger="kupto")
    (ala,) = await household_with("ala")
    fake_llm.rounds += [
        [add_needs_call(("chleb", None, None, "Pieczywo")), Usage(80, 5)],
        LLMUnavailable("boom"),
    ]

    await send(ala, "kup chleb")

    (record,) = usage_records(caplog)
    assert record.outcome == "llm_unavailable"
    assert (record.input_tokens, record.output_tokens, record.model_calls) == (80, 5, 2)


async def test_finish_shopping_via_chat_requires_confirmation(
    household_with, fake_llm, purchase_history
):
    (ala,) = await household_with("ala")
    body = (await ala.post("/api/list/needs", json={"name": "mleko"})).json()
    await ala.post("/api/list/needs", json={"name": "chleb"})
    await ala.post(f"/api/list/items/{list_items(body)['mleko']['id']}/bought")
    fake_llm.rounds += [
        [ToolCall("c1", "request_finish_shopping", "{}")],
        [TextDelta("Przenieść kupione mleko do historii?")],
        [ToolCall("c2", "confirm_finish_shopping", "{}")],
        [TextDelta("Gotowe.")],
    ]

    await send(ala, "skończyłem zakupy")
    assert set(list_items((await ala.get("/api/list")).json())) == {"mleko", "chleb"}
    assert await purchase_history() == []

    assert "nie pytaj ponownie" not in fake_llm.calls[0]["instructions"]
    await send(ala, "tak")
    assert set(list_items((await ala.get("/api/list")).json())) == {"chleb"}
    (trip,) = await purchase_history()
    assert [i.name for i in trip.items] == ["mleko"]
    assert "nie pytaj ponownie" in fake_llm.calls[2]["instructions"]


async def test_too_long_message_is_rejected_without_calling_model(household_with, fake_llm):
    (ala,) = await household_with("ala")

    response, _ = await send(ala, "x" * 8001)

    assert response.status_code == 422
    assert fake_llm.calls == []


RECIPE = "Naleśniki\nSkładniki: 2 szklanki mąki, 0,5 l mleka, 2 jajka, woda, sól.\n" + (
    "Wszystkie składniki zmiksuj na gładkie ciasto i odstaw na 15 minut. " * 60
)


async def test_pasted_recipe_is_proposed_then_missing_ingredients_are_added(
    household_with, fake_llm
):
    (ala,) = await household_with("ala")
    assert 2000 < len(RECIPE) <= 8000
    proposal = "Naleśniki: mąka (2 szklanki), mleko 0,5 l, jajka 2 szt. Czego brakuje?"
    added = [
        {"name": "mleko", "amount": 0.5, "unit": "l", "note": "na: naleśniki"},
        {"name": "jajka", "amount": 2, "unit": "szt", "note": "na: naleśniki"},
    ]
    fake_llm.rounds += [
        [TextDelta(proposal)],
        [
            ToolCall(
                "call_1",
                "add_needs",
                json.dumps({"items": [{**i, "category": "Nabiał"} for i in added]}),
            )
        ],
        [TextDelta("Dodałem mleko i jajka na naleśniki.")],
    ]

    response, _ = await send(ala, RECIPE)
    assert response.status_code == 200
    assert list_items((await ala.get("/api/list")).json()) == {}
    # Cały przepis trafia do modelu, a przy potwierdzeniu model widzi też swoją propozycję.
    assert fake_llm.calls[0]["input"][-1] == {"role": "user", "content": RECIPE}

    _, events = await send(ala, "brakuje mi tylko mleka i jajek")

    assert ("list_changed", {}) in events
    assert fake_llm.calls[1]["input"][-2] == {"role": "assistant", "content": proposal}
    items = list_items((await ala.get("/api/list")).json())
    assert set(items) == {"mleko", "jajka"}
    assert [n["note"] for i in items.values() for n in i["needs"]] == ["na: naleśniki"] * 2


async def test_recipe_saved_via_chat_is_visible_to_household(household_with, fake_llm):
    ala, ola = await household_with("ala", "ola")
    recipe = {
        "name": "Naleśniki",
        "servings": None,
        "source_url": None,
        "instructions": None,
        "ingredients": [
            {"name": "mleko", "amount": 0.5, "unit": "l", "note": None, "category": "Nabiał"},
            {
                "name": "woda",
                "amount": None,
                "unit": None,
                "note": "1 szklanka",
                "category": "Inne",
            },
        ],
    }
    fake_llm.rounds += [
        [ToolCall("call_1", "save_recipe", json.dumps(recipe))],
        [TextDelta("Zapisałem przepis „Naleśniki”.")],
    ]

    response, events = await send(ala, "zapisz ten przepis")

    assert response.status_code == 200
    # Zapis przepisu nie zmienia listy, więc klient nie dostaje sygnału jej zmiany.
    assert ("list_changed", {}) not in events
    assert "saved" in json.loads(fake_llm.calls[1]["input"][-1]["output"])
    recipes = (await ola.get("/api/recipes")).json()
    assert [(r["name"], r["ingredient_count"]) for r in recipes] == [("Naleśniki", 2)]
    assert list_items((await ala.get("/api/list")).json()) == {}


async def test_empty_message_is_rejected(household_with, fake_llm):
    (ala,) = await household_with("ala")

    assert (await send(ala, "   "))[0].status_code == 422
    assert fake_llm.calls == []


async def test_chat_requires_household(login_as, fake_llm):
    ala = await login_as("ala")

    response, _ = await send(ala, "Skończył się chleb")

    assert response.status_code == 409
    assert "gospodarstwo" in response.json()["detail"]
    assert fake_llm.calls == []


async def test_rate_limit(household_with, fake_llm, settings, session):
    (ala,) = await household_with("ala")
    limit = settings.chat_rate_limit_per_hour
    fake_llm.rounds += [[TextDelta("ok")] for _ in range(limit)]
    for _ in range(limit):
        assert (await send(ala, "hej"))[0].status_code == 200
    calls_before = len(fake_llm.calls)

    response, _ = await send(ala, "hej")

    assert response.status_code == 429
    assert 0 < int(response.headers["retry-after"]) <= 3600
    assert len(fake_llm.calls) == calls_before

    # Wiadomości starsze niż godzina nie liczą się do limitu.
    await session.execute(
        update(ChatMessage).values(
            created_at=ChatMessage.created_at - timedelta(hours=1, minutes=1)
        )
    )
    await session.commit()
    fake_llm.rounds.append([TextDelta("ok")])
    assert (await send(ala, "hej"))[0].status_code == 200


async def test_history_is_private_and_persistent(household_with, fake_llm):
    ala, ola = await household_with("ala", "ola")
    fake_llm.rounds.append([TextDelta("Dodam!")])
    await send(ala, "kup chleb")

    ala_history = (await ala.get("/api/chat/messages")).json()
    assert [(m["role"], m["content"]) for m in ala_history] == [
        ("user", "kup chleb"),
        ("assistant", "Dodam!"),
    ]
    assert (await ola.get("/api/chat/messages")).json() == []


async def test_clearing_history_keeps_list(household_with, fake_llm):
    (ala,) = await household_with("ala")
    fake_llm.rounds += [[add_needs_call(("chleb", None, None, "Pieczywo"))], [TextDelta("Dodane")]]
    await send(ala, "kup chleb")

    assert (await ala.delete("/api/chat/messages")).status_code == 204

    assert (await ala.get("/api/chat/messages")).json() == []
    assert "chleb" in list_items((await ala.get("/api/list")).json())


async def test_going_shopping_via_chat_sets_status_for_household(household_with, fake_llm):
    ala, ola = await household_with("ala", "ola")
    await ala.post("/api/list/needs", json={"name": "mleko"})
    fake_llm.rounds += [
        [ToolCall("c1", "start_shopping", "{}")],
        [TextDelta("Udanych zakupów! Do kupienia: mleko.")],
    ]

    _, events = await send(ala, "idę do sklepu")

    assert ("list_changed", {}) in events
    body = (await ola.get("/api/list")).json()
    assert [s["login"] for s in body["shoppers"]] == ["ala"]
    assert set(list_items(body)) == {"mleko"}
    assert "start_shopping" in {t["name"] for t in fake_llm.calls[0]["tools"]}


async def test_model_sees_who_is_shopping(household_with, fake_llm):
    ala, ola = await household_with("ala", "ola")
    await ola.post("/api/list/shopping")
    fake_llm.rounds.append([TextDelta("Zakupy robi ola.")])

    await send(ala, "czy ktoś jest w sklepie?")

    assert '"shopping_now": ["ola"]' in fake_llm.calls[0]["instructions"]


async def test_household_preferences_reach_the_model_and_chat_can_change_them(
    household_with, fake_llm
):
    ala, ola = await household_with("ala", "ola")
    await ola.put("/api/households/me/preferences", json={"people": 4, "excluded": ["orzechy"]})
    change = {
        "people": None,
        "diets": None,
        "excluded": ["orzechy", "seler"],
        "disliked": None,
        "max_cooking_minutes": None,
        "notes": None,
    }
    fake_llm.rounds += [
        [ToolCall("call_1", "update_preferences", json.dumps(change))],
        [TextDelta("Zapamiętałem: bez selera.")],
    ]

    response, events = await send(ala, "zapamiętaj, że Ola nie je selera")

    assert response.status_code == 200
    assert '{"people": 4, "excluded": ["orzechy"]}' in fake_llm.calls[0]["instructions"]
    assert ("list_changed", {}) not in events
    body = (await ola.get("/api/households/me/preferences")).json()
    assert (body["people"], body["excluded"], body["updated_by"]) == (
        4,
        ["orzechy", "seler"],
        "ala",
    )


async def test_meal_plan_saved_via_chat_then_only_missing_ingredients_are_added(
    household_with, fake_llm, monkeypatch
):
    monkeypatch.setattr(meal_plan, "today", lambda: date(2026, 10, 24))
    ala, ola = await household_with("ala", "ola")
    recipe = (
        await ola.post(
            "/api/recipes",
            json={
                "name": "Naleśniki",
                "ingredients": [
                    {"name": "mleko", "amount": 0.5, "unit": "l", "category": "Nabiał"},
                    {"name": "jajka", "amount": 2, "unit": "szt", "category": "Nabiał"},
                ],
            },
        )
    ).json()
    days = [
        {"date": "2026-10-25", "name": "Naleśniki", "recipe_id": recipe["id"]},
        {"date": "2026-10-26", "name": "Zupa pomidorowa", "recipe_id": None},
    ]
    fake_llm.rounds += [
        [ToolCall("call_1", "save_meal_plan", json.dumps({"days": days}))],
        [TextDelta("Zapisałem plan. Składniki: mleko, jajka, pomidory. Czego brakuje?")],
        [
            ToolCall(
                "call_2",
                "add_needs",
                json.dumps(
                    {
                        "items": [
                            {
                                "name": "mleko",
                                "amount": 0.5,
                                "unit": "l",
                                "note": "na: naleśniki",
                                "category": "Nabiał",
                            }
                        ]
                    }
                ),
            )
        ],
        [TextDelta("Dodałem mleko.")],
    ]

    response, events = await send(ala, "tak, zapisz ten plan")

    assert response.status_code == 200
    assert "Dziś jest sobota 2026-10-24." in fake_llm.calls[0]["instructions"]
    # Zapis planu nie zmienia listy, a model dostaje od razu składniki dania z przepisu.
    assert ("list_changed", {}) not in events
    saved = json.loads(fake_llm.calls[1]["input"][-1]["output"])["saved"]
    assert [i["name"] for i in saved[0]["ingredients"]] == ["mleko", "jajka"]
    plan = (
        await ola.get("/api/meal-plan", params={"from": "2026-10-24", "to": "2026-10-31"})
    ).json()
    assert [(e["day"], e["name"], e["recipe_id"], e["planned_by"]) for e in plan] == [
        ("2026-10-25", "Naleśniki", recipe["id"], "ala"),
        ("2026-10-26", "Zupa pomidorowa", None, "ala"),
    ]
    assert list_items((await ala.get("/api/list")).json()) == {}

    _, events = await send(ala, "brakuje tylko mleka")

    assert ("list_changed", {}) in events
    items = list_items((await ala.get("/api/list")).json())
    assert set(items) == {"mleko"}
    assert items["mleko"]["needs"][0]["note"] == "na: naleśniki"

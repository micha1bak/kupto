"""Scenariusz z zadania 9.1: dwóch domowników buduje i zamyka wspólną listę wyłącznie przez czat."""

import json

from kupto.chat.llm import TextDelta, ToolCall


def add_milk(amount: float) -> ToolCall:
    item = {"name": "mleko", "amount": amount, "unit": "l", "note": None, "category": "Nabiał"}
    return ToolCall("add", "add_needs", json.dumps({"items": [item]}))


async def chat(client, content: str) -> None:
    response = await client.post("/api/chat/messages", json={"content": content})
    assert response.status_code == 200
    assert response.text.rstrip().endswith("event: done\ndata: {}")


async def shopping_list(client) -> list[dict]:
    body = (await client.get("/api/list")).json()
    return [item for group in body["groups"] for item in group["items"]]


async def test_two_members_build_and_finish_list_through_chat(household_with, fake_llm):
    ala, ola = await household_with("ala", "ola")

    fake_llm.rounds += [[add_milk(1)], [TextDelta("Dodałem 1 l mleka.")]]
    await chat(ala, "kup litr mleka")
    fake_llm.rounds += [[add_milk(2)], [TextDelta("Mleko już było, dopisałem 2 l.")]]
    await chat(ola, "potrzebuję 2 litry mleka")

    (milk,) = await shopping_list(ala)
    assert milk["name"] == "mleko"
    assert milk["quantities"] == [{"amount": 3.0, "unit": "l"}]
    assert [n["name"] for n in milk["needs"]] == ["ala", "ola"]

    fake_llm.rounds += [
        [ToolCall("buy", "mark_bought", json.dumps({"item_ids": [milk["id"]]}))],
        [TextDelta("Oznaczyłem mleko jako kupione.")],
    ]
    await chat(ala, "kupiłam mleko")
    (milk,) = await shopping_list(ola)
    assert (milk["bought"], milk["bought_by"]) == (True, "ala")

    fake_llm.rounds += [
        [ToolCall("req", "request_finish_shopping", "{}")],
        [TextDelta("Usunąć kupione mleko z listy?")],
    ]
    await chat(ola, "skończyłam zakupy")
    assert len(await shopping_list(ola)) == 1  # bez potwierdzenia nic nie znika

    fake_llm.rounds += [
        [ToolCall("ok", "confirm_finish_shopping", "{}")],
        [TextDelta("Zakupy zakończone.")],
    ]
    await chat(ola, "tak")
    assert await shopping_list(ala) == []

    # Jeden wątek gospodarstwa (#78): ola widzi też rozmowę ali, podpisaną jej imieniem.
    ola_thread = (await ola.get("/api/chat/messages")).json()
    assert ola_thread[-1]["content"] == "Zakupy zakończone."
    assert ("kup litr mleka", "ala", False) in [
        (m["content"], m["author"]["name"], m["mine"]) for m in ola_thread if m["author"]
    ]

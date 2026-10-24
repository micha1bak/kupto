"""Powiadomienia push o zakupach: #29 „idzie na zakupy”, #30 „dopisano w trakcie”,
#31 „zakupy zakończone” — przez REST i przez czat."""

import json
from datetime import timedelta

import pytest
from sqlalchemy import update
from test_chat_api import add_needs_call, list_items, send
from test_push import PRIVATE, PUBLIC, FakePushTransport, subscribe

from kupto.chat.llm import TextDelta, ToolCall
from kupto.config import Settings
from kupto.lists.notifications import ITEMS_ADDED_WINDOW, format_names
from kupto.models import Need, User


@pytest.fixture
def settings(migrated_database: str) -> Settings:
    return Settings(
        database_url=migrated_database,
        jwt_secret="test-secret-that-is-long-enough-for-hs256",
        cookie_secure=False,
        openai_api_key="",
        vapid_public_key=PUBLIC,
        vapid_private_key=PRIVATE,
        vapid_subject="https://kupto.example",
    )


@pytest.fixture
def push_transport() -> FakePushTransport:
    return FakePushTransport()


@pytest.fixture
async def home(app, household_with, push_transport):
    """ala, ola i ewa w jednym gospodarstwie, obcy w innym; każdy ma subskrybowany telefon."""
    ala, ola, ewa = await household_with("ala", "ola", "ewa")
    (obcy,) = await household_with("obcy", name="Inny dom")
    clients = {"ala": ala, "ola": ola, "ewa": ewa, "obcy": obcy}
    for login, client in clients.items():
        await subscribe(client, login)
    return clients


async def received(app, transport: FakePushTransport) -> list[tuple[str, dict, str, str | None]]:
    """Wysłane powiadomienia jako (login adresata, ładunek, pilność, temat); czyści atrapę."""
    await app.state.notifier.drain()
    sent = [
        (s.endpoint.rsplit("/", 1)[-1], json.loads(s.payload), s.urgency, s.topic)
        for s in transport.sent
    ]
    transport.sent.clear()
    return sorted(sent, key=lambda s: s[0])


def recipients(sent) -> list[str]:
    return [login for login, *_ in sent]


async def household_id(client) -> int:
    return (await client.get("/api/households/me")).json()["id"]


# --- treść ---


@pytest.mark.parametrize(
    ("names", "expected"),
    [
        ([], ""),
        (["mleko"], "mleko"),
        (["a", "b", "c", "d", "e"], "a, b, c, d, e"),
        (["a", "b", "c", "d", "e", "f"], "a, b, c, d, e i 1 inny"),
        ([str(i) for i in range(8)], "0, 1, 2, 3, 4 i 3 inne"),
        ([str(i) for i in range(10)], "0, 1, 2, 3, 4 i 5 innych"),
        ([str(i) for i in range(17)], "0, 1, 2, 3, 4 i 12 innych"),
        (["x" * 60], "x" * 39 + "…"),
    ],
)
def test_format_names(names, expected):
    assert format_names(names) == expected


# --- #29 „X idzie na zakupy” ---


async def test_start_notifies_other_members_only(app, home, push_transport):
    await home["ala"].post("/api/list/shopping")

    sent = await received(app, push_transport)

    assert recipients(sent) == ["ewa", "ola"]
    _, payload, urgency, topic = sent[0]
    assert payload["type"] == "shopping_started"
    assert payload["title"] == "ala idzie na zakupy"
    assert payload["body"] == "Dopisz, czego potrzebujesz."
    assert payload["url"] == "/"
    assert topic == payload["tag"] == f"shopping-started-{await household_id(home['ala'])}"
    assert urgency == "normal"


async def test_notification_uses_name_instead_of_login(app, home, push_transport):
    await home["ala"].patch("/api/users/me", json={"name": "Ala K."})

    await home["ala"].post("/api/list/shopping")

    sent = await received(app, push_transport)
    assert sent[0][1]["title"] == "Ala K. idzie na zakupy"


async def test_repeated_start_does_not_notify_again(app, home, push_transport):
    await home["ala"].post("/api/list/shopping")
    await received(app, push_transport)

    await home["ala"].post("/api/list/shopping")

    assert await received(app, push_transport) == []


async def test_start_via_chat_notifies(app, home, push_transport, fake_llm):
    fake_llm.rounds += [[ToolCall("c1", "start_shopping", "{}")], [TextDelta("Udanych zakupów!")]]

    await send(home["ala"], "idę do sklepu")

    sent = await received(app, push_transport)
    assert recipients(sent) == ["ewa", "ola"]
    assert sent[0][1]["title"] == "ala idzie na zakupy"


# --- #30 „Dopisano w trakcie” ---


async def test_added_item_notifies_only_shoppers_other_than_author(app, home, push_transport):
    await home["ola"].post("/api/list/shopping")
    await home["obcy"].post("/api/list/shopping")
    await received(app, push_transport)

    await home["ala"].post("/api/list/needs", json={"name": "mleko"})

    sent = await received(app, push_transport)
    assert recipients(sent) == ["ola"]
    _, payload, urgency, topic = sent[0]
    assert payload["type"] == "items_added"
    assert payload["title"] == "Dopisano w trakcie zakupów"
    assert payload["body"] == "mleko"
    ola_id = (await home["ola"].get("/api/users/me")).json()["id"]
    assert topic == payload["tag"] == f"items-added-{await household_id(home['ola'])}-{ola_id}"
    assert urgency == "high"


async def test_no_shoppers_no_notification(app, home, push_transport):
    await home["ala"].post("/api/list/needs", json={"name": "mleko"})

    assert await received(app, push_transport) == []


async def test_shoppers_own_addition_does_not_notify_them(app, home, push_transport):
    await home["ola"].post("/api/list/shopping")
    await received(app, push_transport)

    await home["ola"].post("/api/list/needs", json={"name": "mleko"})

    assert await received(app, push_transport) == []


async def test_other_household_shopper_is_not_notified(app, home, push_transport):
    await home["obcy"].post("/api/list/shopping")
    await received(app, push_transport)

    await home["ala"].post("/api/list/needs", json={"name": "mleko"})

    assert await received(app, push_transport) == []


async def test_several_additions_update_one_notification(app, home, push_transport):
    await home["ola"].post("/api/list/shopping")
    await received(app, push_transport)

    await home["ala"].post("/api/list/needs", json={"name": "mleko"})
    await home["ewa"].post("/api/list/needs", json={"name": "chleb"})
    await home["ola"].post("/api/list/needs", json={"name": "kawa"})  # własne — pomijane
    await home["ala"].post("/api/list/needs", json={"name": "masło"})

    sent = await received(app, push_transport)
    assert recipients(sent) == ["ola", "ola", "ola"]
    assert [p["body"] for _, p, *_ in sent] == ["mleko", "chleb, mleko", "masło, chleb, mleko"]
    assert len({topic for *_, topic in sent}) == 1  # ten sam tag — zastępują się na urządzeniu


async def test_additions_before_status_start_are_not_listed(app, home, push_transport):
    await home["ala"].post("/api/list/needs", json={"name": "jajka"})
    await home["ola"].post("/api/list/shopping")
    await received(app, push_transport)

    await home["ewa"].post("/api/list/needs", json={"name": "chleb"})

    assert [p["body"] for _, p, *_ in await received(app, push_transport)] == ["chleb"]


async def test_additions_older_than_window_are_not_listed(app, home, push_transport, session):
    await home["ola"].post("/api/list/shopping")
    await home["ala"].post("/api/list/needs", json={"name": "mleko"})
    # mleko dopisane w trakcie zakupów, ale dawniej niż okno grupowania
    await session.execute(
        update(User)
        .where(User.name == "ola")
        .values(shopping_since=User.shopping_since - ITEMS_ADDED_WINDOW * 2)
    )
    await session.execute(
        update(Need).values(created_at=Need.created_at - ITEMS_ADDED_WINDOW - timedelta(minutes=1))
    )
    await session.commit()
    await received(app, push_transport)

    await home["ewa"].post("/api/list/needs", json={"name": "chleb"})

    sent = await received(app, push_transport)
    assert [p["body"] for _, p, *_ in sent] == ["chleb"]


async def test_bought_items_are_not_listed(app, home, push_transport):
    await home["ola"].post("/api/list/shopping")
    body = (await home["ala"].post("/api/list/needs", json={"name": "mleko"})).json()
    await home["ola"].post(f"/api/list/items/{list_items(body)['mleko']['id']}/bought")
    await received(app, push_transport)

    await home["ala"].post("/api/list/needs", json={"name": "chleb"})

    assert [p["body"] for _, p, *_ in await received(app, push_transport)] == ["chleb"]


async def test_addition_via_chat_notifies_shoppers(app, home, push_transport, fake_llm):
    await home["ola"].post("/api/list/shopping")
    await home["ewa"].post("/api/list/shopping")
    await received(app, push_transport)
    fake_llm.rounds += [
        [add_needs_call(("mleko", 2, "l", "Nabiał"), ("chleb", None, None, "Pieczywo"))],
        [TextDelta("Dodane.")],
    ]

    await send(home["ala"], "kup mleko i chleb")

    sent = await received(app, push_transport)
    assert recipients(sent) == ["ewa", "ola"]
    assert {p["body"] for _, p, *_ in sent} == {"chleb, mleko"}  # najnowsze pierwsze


# --- #31 „Zakupy zakończone” ---


async def prepare_list(client, bought: list[str], left: list[str]) -> None:
    for name in bought + left:
        body = (await client.post("/api/list/needs", json={"name": name})).json()
    for name in bought:
        await client.post(f"/api/list/items/{list_items(body)[name]['id']}/bought")


async def test_finish_lists_missing_items_for_others(app, home, push_transport):
    await prepare_list(home["ala"], bought=["mleko"], left=["chleb", "masło"])
    await received(app, push_transport)

    await home["ala"].post("/api/list/finish")

    sent = await received(app, push_transport)
    assert recipients(sent) == ["ewa", "ola"]
    _, payload, _, topic = sent[0]
    assert payload["type"] == "shopping_finished"
    assert payload["title"] == "ala: zakupy zakończone"
    assert payload["body"] == "Nie było: chleb, masło."
    assert topic == payload["tag"] == f"shopping-finished-{await household_id(home['ala'])}"


async def test_finish_with_everything_bought(app, home, push_transport):
    await prepare_list(home["ala"], bought=["mleko", "chleb"], left=[])
    await received(app, push_transport)

    await home["ala"].post("/api/list/finish")

    sent = await received(app, push_transport)
    assert recipients(sent) == ["ewa", "ola"]
    assert sent[0][1]["body"] == "Wszystko kupione."


async def test_finish_without_bought_items_does_not_notify(app, home, push_transport):
    await prepare_list(home["ala"], bought=[], left=["chleb"])
    await home["ala"].post("/api/list/shopping")
    await received(app, push_transport)

    await home["ala"].post("/api/list/finish")

    assert await received(app, push_transport) == []


async def test_finish_via_chat_notifies(app, home, push_transport, fake_llm):
    await prepare_list(home["ala"], bought=["mleko"], left=["chleb"])
    await received(app, push_transport)
    fake_llm.rounds += [
        [ToolCall("c1", "request_finish_shopping", "{}")],
        [TextDelta("Przenieść kupione mleko do historii?")],
        [ToolCall("c2", "confirm_finish_shopping", "{}")],
        [TextDelta("Gotowe.")],
    ]

    await send(home["ala"], "skończyłem zakupy")
    assert await received(app, push_transport) == []
    await send(home["ala"], "tak")

    sent = await received(app, push_transport)
    assert recipients(sent) == ["ewa", "ola"]
    assert sent[0][1]["body"] == "Nie było: chleb."

"""Lista na żywo: publikacja NOTIFY z serwisów i rozprowadzanie przez broker LISTEN."""

import asyncio
import json

import asyncpg
import pytest
from sqlalchemy import func, select, text

from kupto.chat.llm import TextDelta, ToolCall
from kupto.lists import events
from kupto.lists.events import BrokerUnavailable, ListEventBroker, Subscription
from kupto.models import User

QUIET = 0.3  # ile czekamy, by stwierdzić, że sygnał nie przyszedł


async def user_ids(session, *logins):
    rows = await session.execute(select(User.login, User.id, User.household_id))
    by_login = {login: (user_id, household_id) for login, user_id, household_id in rows}
    return [by_login[login] for login in logins]


@pytest.fixture
async def broker(app):
    broker: ListEventBroker = app.state.list_events
    await broker.wait_ready(5)
    return broker


@pytest.fixture
def subscribe(broker, session):
    """Subskrypcja w imieniu członka (po loginie), tak jak robi to strumień SSE."""

    async def factory(login: str) -> Subscription:
        ((user_id, household_id),) = await user_ids(session, login)
        return broker.subscribe(household_id, user_id)

    return factory


async def assert_signal(subscription: Subscription) -> None:
    assert await subscription.wait(5), "brak sygnału zmiany listy"
    assert not subscription.closed


async def assert_quiet(subscription: Subscription) -> None:
    assert not await subscription.wait(QUIET), "nieoczekiwany sygnał zmiany listy"
    assert not subscription.closed


async def test_change_reaches_members_of_the_same_household_only(household_with, subscribe):
    ala, ola = await household_with("ala", "ola")
    (ewa,) = await household_with("ewa", name="Sąsiedzi")
    ola_stream, ewa_stream = await subscribe("ola"), await subscribe("ewa")

    await ala.post("/api/list/needs", json={"name": "mleko"})

    await assert_signal(ola_stream)
    await assert_quiet(ewa_stream)

    await ewa.post("/api/list/needs", json={"name": "chleb"})

    await assert_signal(ewa_stream)
    await assert_quiet(ola_stream)


async def test_every_list_operation_publishes(household_with, subscribe):
    ala, ola = await household_with("ala", "ola")
    stream = await subscribe("ola")
    body = (await ala.post("/api/list/needs", json={"name": "mleko", "amount": 1})).json()
    await assert_signal(stream)
    item = body["groups"][0]["items"][0]
    need_id = item["needs"][0]["id"]

    operations = [
        ala.patch(f"/api/list/needs/{need_id}", json={"amount": 2}),
        ala.post(f"/api/list/items/{item['id']}/bought"),
        ala.delete(f"/api/list/items/{item['id']}/bought"),
        ala.post(f"/api/list/items/{item['id']}/bought"),
        ala.post("/api/list/finish"),
    ]
    for operation in operations:
        assert (await operation).status_code == 200
        await assert_signal(stream)

    body = (await ala.post("/api/list/needs", json={"name": "chleb"})).json()
    await assert_signal(stream)
    bread = body["groups"][0]["items"][0]
    assert (await ala.delete(f"/api/list/needs/{bread['needs'][0]['id']}")).status_code == 200
    await assert_signal(stream)

    await ala.post("/api/list/needs", json={"name": "masło"})
    await assert_signal(stream)
    body = (await ala.get("/api/list")).json()
    butter = body["groups"][0]["items"][0]
    assert (await ala.delete(f"/api/list/items/{butter['id']}")).status_code == 200
    await assert_signal(stream)


async def test_failed_or_empty_operations_do_not_publish(household_with, subscribe):
    (ala,) = await household_with("ala")
    stream = await subscribe("ala")

    assert (await ala.post("/api/list/items/999/bought")).status_code == 404
    assert (await ala.post("/api/list/finish")).status_code == 200  # nic do przeniesienia

    await assert_quiet(stream)


async def test_chat_tools_publish_list_changes(household_with, subscribe, fake_llm):
    ala, ola = await household_with("ala", "ola")
    stream = await subscribe("ola")
    payload = {"items": [{"name": "mleko", "amount": None, "unit": None, "note": None}]}
    fake_llm.rounds += [
        [ToolCall("call_1", "add_needs", json.dumps({**payload}))],
        [TextDelta("Dodałem mleko.")],
    ]

    response = await ala.post("/api/chat/messages", json={"content": "Dodaj mleko"})

    assert response.status_code == 200
    await assert_signal(stream)


async def test_category_order_change_reaches_only_own_streams(household_with, subscribe):
    ala, ola = await household_with("ala", "ola")
    ala_phone, ala_laptop, ola_stream = (
        await subscribe("ala"),
        await subscribe("ala"),
        await subscribe("ola"),
    )

    response = await ala.put(
        "/api/list/category-order/Nabiał", json={"after": None, "before": "Warzywa i owoce"}
    )

    assert response.status_code == 200
    await assert_signal(ala_phone)
    await assert_signal(ala_laptop)
    await assert_quiet(ola_stream)

    for request in (
        ala.delete("/api/list/category-order/Nabiał"),
        ala.delete("/api/list/category-order"),
    ):
        assert (await request).status_code == 200
        await assert_signal(ala_phone)
    await assert_quiet(ola_stream)


async def test_removed_member_stream_is_closed(household_with, subscribe, session):
    ala, ola = await household_with("ala", "ola")
    ala_stream, ola_stream = await subscribe("ala"), await subscribe("ola")
    ((ola_id, _),) = await user_ids(session, "ola")

    assert (await ala.delete(f"/api/households/me/members/{ola_id}")).status_code == 200

    assert await ola_stream.wait(5)
    assert ola_stream.closed
    await assert_quiet(ala_stream)

    await ala.post("/api/list/needs", json={"name": "mleko"})
    await assert_signal(ala_stream)


async def test_leaving_household_closes_own_stream(household_with, subscribe):
    ala, ola = await household_with("ala", "ola")
    ola_stream = await subscribe("ola")

    assert (await ola.post("/api/households/me/leave")).status_code == 204

    assert await ola_stream.wait(5)
    assert ola_stream.closed


async def test_notification_is_delivered_only_after_commit(app, broker, session, household_with):
    (ala,) = await household_with("ala")
    ((ala_id, household_id),) = await user_ids(session, "ala")
    stream = broker.subscribe(household_id, ala_id)

    async with app.state.sessionmaker() as tx:
        await events.list_changed(tx, household_id)
        await assert_quiet(stream)
        await tx.rollback()
    await assert_quiet(stream)

    async with app.state.sessionmaker() as tx:
        await events.list_changed(tx, household_id)
        await tx.commit()
    await assert_signal(stream)


async def test_lost_listen_connection_closes_streams_and_reconnects(
    app, broker, session, household_with
):
    (ala,) = await household_with("ala")
    ((ala_id, household_id),) = await user_ids(session, "ala")
    stream = broker.subscribe(household_id, ala_id)
    listener_pids = list(
        await session.scalars(text("SELECT pid FROM pg_stat_activity WHERE query LIKE 'LISTEN%'"))
    )
    assert listener_pids

    for pid in listener_pids:
        await session.execute(select(func.pg_terminate_backend(pid)))

    assert await stream.wait(5)
    assert stream.closed
    await broker.wait_ready(10)
    new_stream = broker.subscribe(household_id, ala_id)
    await ala.post("/api/list/needs", json={"name": "mleko"})
    await assert_signal(new_stream)


async def test_broker_without_database_is_unavailable():
    broker = ListEventBroker("postgresql+asyncpg://kupto:kupto@127.0.0.1:1/kupto", retry_delay=0.05)
    try:
        with pytest.raises(BrokerUnavailable):
            await broker.wait_ready(0.3)
        with pytest.raises(BrokerUnavailable):
            broker.subscribe(1, 1)
    finally:
        await broker.close()


async def test_invalid_notification_is_ignored(broker, database_url):
    connection = await asyncpg.connect(database_url.replace("+asyncpg", ""))
    try:
        await connection.execute("SELECT pg_notify($1, 'nie-json')", events.CHANNEL)
        await asyncio.sleep(QUIET)
    finally:
        await connection.close()
    await broker.wait_ready(1)  # broker działa dalej


async def test_shopping_status_changes_publish(household_with, subscribe):
    ala, _ = await household_with("ala", "ola")
    stream = await subscribe("ola")

    assert (await ala.post("/api/list/shopping")).status_code == 200
    await assert_signal(stream)
    assert (await ala.post("/api/list/shopping")).status_code == 200  # już aktywny — bez zmian
    await assert_quiet(stream)
    assert (await ala.delete("/api/list/shopping")).status_code == 200
    await assert_signal(stream)
    assert (await ala.delete("/api/list/shopping")).status_code == 200
    await assert_quiet(stream)

    # Zakończenie zakupów bez kupionych pozycji zdejmuje status — to też zmiana listy.
    await ala.post("/api/list/shopping")
    await assert_signal(stream)
    assert (await ala.post("/api/list/finish")).status_code == 200
    await assert_signal(stream)


async def test_leaving_shopper_publishes_to_remaining_members(household_with, subscribe):
    ala, ola = await household_with("ala", "ola")
    stream = await subscribe("ala")
    await ola.post("/api/list/shopping")
    await assert_signal(stream)

    assert (await ola.post("/api/households/me/leave")).status_code == 204

    await assert_signal(stream)


async def test_chat_shopping_tools_publish(household_with, subscribe, fake_llm):
    ala, _ = await household_with("ala", "ola")
    stream = await subscribe("ola")
    fake_llm.rounds += [
        [ToolCall("call_1", "start_shopping", "{}")],
        [TextDelta("Powodzenia!")],
    ]

    response = await ala.post("/api/chat/messages", json={"content": "Idę na zakupy"})

    assert response.status_code == 200
    await assert_signal(stream)

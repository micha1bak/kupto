"""Przypomnienia push o zwykłych produktach (#40): treść, adresaci, limity i komenda."""

import asyncio
import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from test_push import PRIVATE, PUBLIC, FakePushTransport, endpoint, subscribe
from test_usual import NOW, add_trip, weekly

from kupto.config import Settings
from kupto.history import reminders
from kupto.history.reminders import in_send_window, send_reminders
from kupto.models import Household, UsualReminder

DAY = timedelta(days=1)


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


async def enable(client, enabled: bool = True) -> None:
    response = await client.put("/api/push/preferences/usual_reminder", json={"enabled": enabled})
    assert response.status_code == 200, response.text


async def household_of(session, client) -> Household:
    household_id = (await client.get("/api/households/me")).json()["id"]
    return await session.get(Household, household_id)


@pytest.fixture
async def home(household_with, session):
    """ala i ola w jednym gospodarstwie, każda z telefonem; przypomnienia włączyła tylko ala."""
    ala, ola = await household_with("ala", "ola")
    for login, client in {"ala": ala, "ola": ola}.items():
        await subscribe(client, login)
    await enable(ala)
    return {"ala": ala, "ola": ola, "household": await household_of(session, ala)}


async def remind(app, transport: FakePushTransport, now: datetime) -> list[tuple[str, dict]]:
    """Uruchamia wysyłkę na chwilę `now`; zwraca (login adresata, ładunek) i czyści atrapę."""
    transport.sent.clear()
    await send_reminders(app.state.sessionmaker, app.state.notifier, now)
    sent = sorted(
        (s.endpoint.rsplit("/", 1)[-1], json.loads(s.payload), s.ttl, s.topic)
        for s in transport.sent
    )
    transport.sent.clear()
    return [(login, payload) for login, payload, *_ in sent]


async def reminded(session) -> dict[str, datetime]:
    session.expire_all()
    rows = await session.execute(select(UsualReminder.normalized_name, UsualReminder.reminded_at))
    return {name: reminded_at for name, reminded_at in rows}


# --- treść i adresaci ---


async def test_reminder_for_missing_usual_product(app, home, session, push_transport):
    await weekly(session, home["household"], "mleko")

    push_transport.sent.clear()
    await send_reminders(app.state.sessionmaker, app.state.notifier, NOW)

    (sent,) = push_transport.sent
    assert sent.endpoint.endswith("/ala")  # ola nie włączyła przypomnień
    tag = f"usual-reminder-{home['household'].id}"
    assert json.loads(sent.payload) == {
        "type": "usual_reminder",
        "title": "Zwykle o tej porze kupujecie",
        "body": "mleko — dopisać do listy?",
        "url": "/",
        "tag": tag,
    }
    assert (sent.topic, sent.ttl, sent.urgency) == (tag, 4 * 3600, "normal")
    assert await reminded(session) == {"mleko": NOW}


async def test_no_reminder_when_nothing_is_missing(app, home, session, push_transport):
    await weekly(session, home["household"], "mleko")
    await weekly(session, home["household"], "chleb", last_days_ago=1)  # jeszcze za wcześnie
    await home["ala"].post("/api/list/needs", json={"name": "mleko"})

    assert await remind(app, push_transport, NOW) == []
    assert await reminded(session) == {}


async def test_households_are_isolated(app, home, household_with, session, push_transport):
    ewa, ewy_ola = await household_with("ewa", "ewy_ola", name="Sąsiedzi")
    await subscribe(ewa, "ewa")
    await enable(ewa)
    await weekly(session, await household_of(session, ewa), "kawa")

    sent = await remind(app, push_transport, NOW)

    assert [(login, payload["body"]) for login, payload in sent] == [
        ("ewa", "kawa — dopisać do listy?")
    ]


async def test_disabled_by_default_and_opt_in_later(app, home, session, push_transport):
    await enable(home["ala"], False)
    await weekly(session, home["household"], "mleko")

    assert await remind(app, push_transport, NOW) == []
    # Pominięcie niczego nie zapisuje — po włączeniu przychodzi to, czego brakowało już wcześniej.
    assert await reminded(session) == {}

    await enable(home["ola"])
    sent = await remind(app, push_transport, NOW + DAY)

    assert [login for login, _ in sent] == ["ola"]


async def test_member_without_device_does_not_count(app, home, session):
    response = await home["ala"].request(
        "DELETE", "/api/push/subscriptions", json={"endpoint": endpoint("ala")}
    )
    assert response.status_code == 204
    await weekly(session, home["household"], "mleko")

    await send_reminders(app.state.sessionmaker, app.state.notifier, NOW)

    assert await reminded(session) == {}


# --- limity ---


async def test_at_most_one_reminder_per_day(app, home, session, push_transport):
    household = home["household"]
    await weekly(session, household, "mleko")
    assert len(await remind(app, push_transport, NOW)) == 1

    # Nowy brakujący produkt tego samego dnia też czeka do jutra.
    await weekly(session, household, "chleb", last_days_ago=7.2)
    assert await remind(app, push_transport, NOW + timedelta(hours=6)) == []
    assert await reminded(session) == {"mleko": NOW}


async def test_same_products_are_not_repeated(app, home, session, push_transport):
    await weekly(session, home["household"], "mleko")
    assert len(await remind(app, push_transport, NOW)) == 1

    assert await remind(app, push_transport, NOW + DAY) == []
    assert await remind(app, push_transport, NOW + 2 * DAY) == []


async def test_new_product_comes_with_the_old_ones(app, home, session, push_transport):
    household = home["household"]
    await weekly(session, household, "mleko", last_days_ago=7.5)
    await weekly(session, household, "chleb", last_days_ago=5)  # 0,71 odstępu — jeszcze nie
    assert len(await remind(app, push_transport, NOW)) == 1

    ((_, payload),) = await remind(app, push_transport, NOW + DAY)

    # Nowy produkt pierwszy, potem przypomniany już wcześniej.
    assert payload["body"] == "chleb, mleko — dopisać do listy?"
    assert await reminded(session) == {"mleko": NOW + DAY, "chleb": NOW + DAY}


async def test_product_returns_after_next_purchase(app, home, session, push_transport):
    household = home["household"]
    await weekly(session, household, "mleko")
    assert len(await remind(app, push_transport, NOW)) == 1

    await add_trip(session, household, NOW + DAY, "mleko")
    assert await remind(app, push_transport, NOW + 2 * DAY) == []  # właśnie kupione

    ((_, payload),) = await remind(app, push_transport, NOW + 8 * DAY)
    assert payload["body"] == "mleko — dopisać do listy?"


async def test_no_reminders_at_night(app, home, session, push_transport):
    await weekly(session, home["household"], "mleko")
    night = datetime(2026, 10, 22, 1, 0, tzinfo=UTC)  # 3:00 czasu polskiego

    assert await remind(app, push_transport, night) == []
    assert await reminded(session) == {}
    # Ten sam dzień o zwykłej porze.
    assert len(await remind(app, push_transport, NOW)) == 1


async def test_parallel_runs_send_once(app, home, session, push_transport):
    await weekly(session, home["household"], "mleko")
    push_transport.sent.clear()

    await asyncio.gather(
        send_reminders(app.state.sessionmaker, app.state.notifier, NOW),
        send_reminders(app.state.sessionmaker, app.state.notifier, NOW),
    )

    assert len(push_transport.sent) == 1


@pytest.mark.parametrize(
    ("moment", "expected"),
    [
        (datetime(2026, 10, 22, 6, 59, tzinfo=UTC), False),  # 8:59 czasu letniego
        (datetime(2026, 10, 22, 7, 0, tzinfo=UTC), True),  # 9:00
        (datetime(2026, 10, 22, 18, 59, tzinfo=UTC), True),  # 20:59
        (datetime(2026, 10, 22, 19, 0, tzinfo=UTC), False),  # 21:00
        (datetime(2026, 12, 1, 7, 59, tzinfo=UTC), False),  # 8:59 czasu zimowego
        (datetime(2026, 12, 1, 8, 0, tzinfo=UTC), True),  # 9:00
        (datetime(2026, 12, 1, 19, 59, tzinfo=UTC), True),  # 20:59
        (datetime(2026, 12, 1, 20, 0, tzinfo=UTC), False),  # 21:00
    ],
)
def test_send_window_in_polish_time(moment, expected):
    assert in_send_window(moment) is expected


# --- komenda ---


async def test_command_sends_reminders(app, home, session, settings):
    await weekly(session, home["household"], "mleko")
    transport = FakePushTransport()

    assert await reminders.run(settings, transport=transport, now=NOW) == 1

    assert [s.endpoint.rsplit("/", 1)[-1] for s in transport.sent] == ["ala"]
    assert transport.closed


async def test_command_without_vapid_keys_does_nothing(app, home, session, settings):
    await weekly(session, home["household"], "mleko")
    no_push = settings.model_copy(update={"vapid_private_key": "", "vapid_public_key": ""})

    assert await reminders.run(no_push, transport=FakePushTransport(), now=NOW) == 0
    assert await reminded(session) == {}

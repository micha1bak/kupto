import logging
import os
from dataclasses import dataclass, field

import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from sqlalchemy import select

from kupto.config import Settings
from kupto.models import PushSubscription, User
from kupto.push.keys import b64url, generate
from kupto.push.notification import Notification, NotificationType
from kupto.push.notifier import Target
from kupto.push.subscriptions import MAX_SUBSCRIPTIONS_PER_USER

PUBLIC, PRIVATE = generate()
UA = "Mozilla/5.0 (Linux; Android 15) Chrome/140 Mobile"


@dataclass
class Sent:
    endpoint: str
    payload: str
    ttl: int
    urgency: str
    topic: str | None


@dataclass
class FakePushTransport:
    """Atrapa usługi push: zapisuje wysyłki, odpowiada kodem z `responses` (domyślnie 201)."""

    responses: dict[str, int | Exception] = field(default_factory=dict)
    sent: list[Sent] = field(default_factory=list)
    closed: bool = False

    async def send(self, target: Target, payload: str, *, ttl, urgency, topic) -> int:
        self.sent.append(Sent(target.endpoint, payload, ttl, urgency, topic))
        response = self.responses.get(target.endpoint, 201)
        if isinstance(response, Exception):
            raise response
        return response

    async def aclose(self) -> None:
        self.closed = True


@pytest.fixture
def settings(migrated_database: str) -> Settings:
    return Settings(
        database_url=migrated_database,
        jwt_secret="test-secret-that-is-long-enough-for-hs256",
        cookie_secure=False,
        vapid_public_key=PUBLIC,
        vapid_private_key=PRIVATE,
        vapid_subject="https://kupto.example",
    )


@pytest.fixture
def push_transport() -> FakePushTransport:
    return FakePushTransport()


def subscription(device: str) -> dict:
    p256dh = ec.generate_private_key(ec.SECP256R1()).public_key()
    return {
        "endpoint": f"https://fcm.googleapis.com/fcm/send/{device}",
        "expirationTime": None,
        "keys": {
            "p256dh": b64url(p256dh.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)),
            "auth": b64url(os.urandom(16)),
        },
    }


def endpoint(device: str) -> str:
    return subscription(device)["endpoint"]


async def subscribe(client, device: str) -> None:
    response = await client.put(
        "/api/push/subscriptions", json=subscription(device), headers={"User-Agent": UA}
    )
    assert response.status_code == 204, response.text


async def stored(app) -> dict[str, int]:
    """Endpoint → id właściciela dla wszystkich zapisanych subskrypcji."""
    async with app.state.sessionmaker() as session:
        rows = await session.execute(select(PushSubscription.endpoint, PushSubscription.user_id))
        return {endpoint: owner for endpoint, owner in rows}


async def user_id(app, login: str) -> int:
    async with app.state.sessionmaker() as session:
        return await session.scalar(select(User.id).where(User.name == login))


def notification(**overrides) -> Notification:
    return Notification(
        **{"type": NotificationType.SHOPPING_STARTED, "title": "Zakupy", "body": "ala idzie"}
        | overrides
    )


# --- API subskrypcji ---


async def test_public_key(login_as):
    ala = await login_as("ala")

    response = await ala.get("/api/push/public-key")

    assert response.status_code == 200
    assert response.json() == {"public_key": PUBLIC}


async def test_requires_login(client):
    assert (await client.get("/api/push/public-key")).status_code == 401
    put = await client.put("/api/push/subscriptions", json=subscription("a"))
    assert put.status_code == 401
    delete = await client.request("DELETE", "/api/push/subscriptions", json={"endpoint": "x"})
    assert delete.status_code == 401


async def test_user_can_have_several_devices(app, login_as):
    ala = await login_as("ala")

    await subscribe(ala, "telefon")
    await subscribe(ala, "laptop")

    ala_id = await user_id(app, "ala")
    assert await stored(app) == {endpoint("telefon"): ala_id, endpoint("laptop"): ala_id}
    async with app.state.sessionmaker() as session:
        row = await session.scalar(select(PushSubscription).limit(1))
    assert row.user_agent == UA


async def test_resubscribing_updates_and_moves_device_to_current_user(app, login_as):
    ala = await login_as("ala")
    ola = await login_as("ola")
    await subscribe(ala, "wspolny")
    await subscribe(ala, "wspolny")  # ponowny zapis tego samego urządzenia nie dubluje

    await subscribe(ola, "wspolny")

    assert await stored(app) == {endpoint("wspolny"): await user_id(app, "ola")}


async def test_delete_only_own_subscription(app, login_as):
    ala = await login_as("ala")
    ola = await login_as("ola")
    await subscribe(ala, "telefon")
    await subscribe(ola, "tablet")

    foreign = await ola.request(
        "DELETE", "/api/push/subscriptions", json={"endpoint": endpoint("telefon")}
    )
    own = await ola.request(
        "DELETE", "/api/push/subscriptions", json={"endpoint": endpoint("tablet")}
    )
    again = await ola.request(
        "DELETE", "/api/push/subscriptions", json={"endpoint": endpoint("tablet")}
    )

    assert (foreign.status_code, own.status_code, again.status_code) == (204, 204, 204)
    assert await stored(app) == {endpoint("telefon"): await user_id(app, "ala")}


@pytest.mark.parametrize(
    "url",
    [
        "http://fcm.googleapis.com/fcm/send/x",
        "https://localhost/push",
        "https://169.254.169.254/latest",
        "https://evil.example/fcm.googleapis.com",
        "https://googleapis.com.evil.example/x",
        "https://fcm.googleapis.com:8443/x",
        "https://user@fcm.googleapis.com/x",
        "https://fcm.googleapis.com/" + "x" * 2048,  # za długi
    ],
)
async def test_rejects_unknown_push_services(app, login_as, url):
    ala = await login_as("ala")

    response = await ala.put("/api/push/subscriptions", json=subscription("a") | {"endpoint": url})

    assert response.status_code == 422
    assert await stored(app) == {}


@pytest.mark.parametrize(
    "url",
    [
        "https://updates.push.services.mozilla.com/wpush/v2/abc",
        "https://web.push.apple.com/QGx",
        "https://wns2-par02p.notify.windows.com/w/?token=abc",
    ],
)
async def test_accepts_browser_push_services(login_as, url):
    ala = await login_as("ala")

    response = await ala.put("/api/push/subscriptions", json=subscription("a") | {"endpoint": url})

    assert response.status_code == 204


@pytest.mark.parametrize(
    "keys",
    [
        {"p256dh": b64url(b"\x05" + os.urandom(64)), "auth": b64url(os.urandom(16))},
        {"p256dh": subscription("a")["keys"]["p256dh"], "auth": b64url(os.urandom(8))},
        {"p256dh": "nie base64!", "auth": b64url(os.urandom(16))},
    ],
)
async def test_rejects_invalid_keys(app, login_as, keys):
    ala = await login_as("ala")

    response = await ala.put("/api/push/subscriptions", json=subscription("a") | {"keys": keys})

    assert response.status_code == 422
    assert await stored(app) == {}


async def test_keeps_only_newest_devices_per_user(app, login_as):
    ala = await login_as("ala")

    for n in range(MAX_SUBSCRIPTIONS_PER_USER + 2):
        await subscribe(ala, f"d{n}")

    assert set(await stored(app)) == {
        endpoint(f"d{n}") for n in range(2, MAX_SUBSCRIPTIONS_PER_USER + 2)
    }


# --- Wysyłka ---


async def test_send_to_household_skips_author_and_other_households(
    app, household_with, push_transport
):
    ala, ola, ewa = await household_with("ala", "ola", "ewa")
    (obcy,) = await household_with("obcy", name="Inny dom")
    await subscribe(ala, "ala-telefon")
    await subscribe(ola, "ola-telefon")
    await subscribe(ola, "ola-laptop")
    await subscribe(obcy, "obcy-telefon")
    household_id = (await ala.get("/api/households/me")).json()["id"]

    app.state.notifier.send_to_household(
        household_id,
        notification(tag="shopping-started", urgency="high", ttl=600),
        exclude_user_ids={await user_id(app, "ala")},
    )
    await app.state.notifier.drain()

    assert sorted(s.endpoint for s in push_transport.sent) == [
        endpoint("ola-laptop"),
        endpoint("ola-telefon"),
    ]
    sent = push_transport.sent[0]
    assert (sent.ttl, sent.urgency, sent.topic) == (600, "high", "shopping-started")
    assert '"title": "Zakupy"' in sent.payload


async def test_send_to_users(app, login_as, push_transport):
    ala = await login_as("ala")
    ola = await login_as("ola")
    await subscribe(ala, "ala-telefon")
    await subscribe(ola, "ola-telefon")

    app.state.notifier.send_to_users([await user_id(app, "ola")], notification())
    await app.state.notifier.drain()

    assert [s.endpoint for s in push_transport.sent] == [endpoint("ola-telefon")]


@pytest.mark.parametrize("status", [404, 410])
async def test_gone_subscription_is_removed_and_others_delivered(
    app, login_as, push_transport, status
):
    ala = await login_as("ala")
    await subscribe(ala, "stary")
    await subscribe(ala, "nowy")
    push_transport.responses[endpoint("stary")] = status

    app.state.notifier.send_to_users([await user_id(app, "ala")], notification())
    await app.state.notifier.drain()

    assert len(push_transport.sent) == 2
    assert set(await stored(app)) == {endpoint("nowy")}


async def test_errors_and_timeouts_keep_subscriptions(app, login_as, push_transport, caplog):
    ala = await login_as("ala")
    for device in ("wolny", "blad", "awaria", "ok"):
        await subscribe(ala, device)
    push_transport.responses |= {
        endpoint("wolny"): TimeoutError(),
        endpoint("blad"): 500,
        endpoint("awaria"): ConnectionError("brak sieci"),
    }

    with caplog.at_level(logging.WARNING):
        app.state.notifier.send_to_users([await user_id(app, "ala")], notification())
        await app.state.notifier.drain()

    assert len(push_transport.sent) == 4
    assert len(await stored(app)) == 4
    assert "limit czasu" in caplog.text
    # Pełny adres subskrypcji (uprawnienie do wysyłki) nie trafia do logów.
    assert "/fcm/send/" not in caplog.text


async def test_sending_does_not_block_the_caller(app, login_as, push_transport):
    ala = await login_as("ala")
    await subscribe(ala, "telefon")

    app.state.notifier.send_to_users([await user_id(app, "ala")], notification())

    assert push_transport.sent == []  # zaplanowane, jeszcze nie wysłane
    await app.state.notifier.drain()
    assert len(push_transport.sent) == 1


async def test_close_drains_and_closes_transport(app, login_as, push_transport):
    ala = await login_as("ala")
    await subscribe(ala, "telefon")
    app.state.notifier.send_to_users([await user_id(app, "ala")], notification())

    await app.state.notifier.aclose()

    assert len(push_transport.sent) == 1
    assert push_transport.closed

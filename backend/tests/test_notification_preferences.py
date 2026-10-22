"""Ustawienia typów powiadomień per użytkownik (#32): API i respektowanie przy wysyłce."""

import pytest
from test_push import PRIVATE, PUBLIC, FakePushTransport, notification, subscribe, user_id
from test_shopping_notifications import prepare_list, received, recipients

from kupto.config import Settings
from kupto.push import preferences
from kupto.push.notification import NotificationType

# Przypomnienia o zwykłych produktach (#40) są domyślnie wyłączone, pozostałe typy włączone.
DEFAULTS = {
    "types": [
        {"type": "shopping_started", "enabled": True},
        {"type": "items_added", "enabled": True},
        {"type": "shopping_finished", "enabled": True},
        {"type": "usual_reminder", "enabled": False},
    ]
}


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
async def home(household_with):
    """ala, ola i ewa w jednym gospodarstwie; każde ma subskrybowany telefon."""
    ala, ola, ewa = await household_with("ala", "ola", "ewa")
    clients = {"ala": ala, "ola": ola, "ewa": ewa}
    for login, client in clients.items():
        await subscribe(client, login)
    return clients


async def set_preference(client, notification_type: str, enabled: bool):
    return await client.put(f"/api/push/preferences/{notification_type}", json={"enabled": enabled})


# --- API ---


async def test_defaults(login_as):
    ala = await login_as("ala")

    response = await ala.get("/api/push/preferences")

    assert response.status_code == 200
    assert response.json() == DEFAULTS


async def test_disabling_one_type_keeps_others_and_other_users(login_as):
    ala = await login_as("ala")
    ola = await login_as("ola")

    response = await set_preference(ala, "shopping_started", False)

    assert response.status_code == 200
    expected = {"types": [{"type": "shopping_started", "enabled": False}, *DEFAULTS["types"][1:]]}
    assert response.json() == expected
    # Ten sam stan przy kolejnym odczycie (np. na innym urządzeniu), u oli bez zmian.
    assert (await ala.get("/api/push/preferences")).json() == expected
    assert (await ola.get("/api/push/preferences")).json() == DEFAULTS


async def test_setting_is_idempotent_and_reversible(login_as):
    ala = await login_as("ala")

    await set_preference(ala, "items_added", False)
    await set_preference(ala, "items_added", False)
    response = await set_preference(ala, "items_added", True)

    assert response.json() == DEFAULTS


async def test_reminders_can_be_enabled(login_as):
    ala = await login_as("ala")

    response = await set_preference(ala, "usual_reminder", True)

    assert response.status_code == 200
    assert response.json() == {
        "types": [*DEFAULTS["types"][:3], {"type": "usual_reminder", "enabled": True}]
    }


async def test_unknown_type_is_rejected(login_as):
    ala = await login_as("ala")

    response = await set_preference(ala, "spam", False)

    assert response.status_code == 422
    assert (await ala.get("/api/push/preferences")).json() == DEFAULTS


@pytest.mark.parametrize("enabled", ["nie", None])
async def test_invalid_body_is_rejected(login_as, enabled):
    ala = await login_as("ala")

    response = await ala.put("/api/push/preferences/items_added", json={"enabled": enabled})

    assert response.status_code == 422


async def test_requires_login(client):
    assert (await client.get("/api/push/preferences")).status_code == 401
    assert (await set_preference(client, "items_added", False)).status_code == 401


async def test_works_without_household(login_as):
    ala = await login_as("ala")

    assert (await set_preference(ala, "shopping_finished", False)).status_code == 200


# --- Wysyłka ---


async def test_disabled_type_skips_user_in_household_notification(app, home, push_transport):
    await set_preference(home["ola"], "shopping_started", False)

    await home["ala"].post("/api/list/shopping")

    sent = await received(app, push_transport)
    assert recipients(sent) == ["ewa"]


async def test_other_types_still_arrive(app, home, push_transport):
    await set_preference(home["ola"], "shopping_started", False)
    await prepare_list(home["ala"], bought=["mleko"], left=["chleb"])
    await received(app, push_transport)

    await home["ala"].post("/api/list/finish")

    assert recipients(await received(app, push_transport)) == ["ewa", "ola"]


async def test_disabled_type_skips_shopper(app, home, push_transport):
    await set_preference(home["ola"], "items_added", False)
    await home["ola"].post("/api/list/shopping")
    await home["ewa"].post("/api/list/shopping")
    await received(app, push_transport)

    await home["ala"].post("/api/list/needs", json={"name": "mleko"})

    assert recipients(await received(app, push_transport)) == ["ewa"]


async def test_reenabled_type_arrives_again(app, home, push_transport):
    await set_preference(home["ola"], "shopping_started", False)
    await set_preference(home["ola"], "shopping_started", True)

    await home["ala"].post("/api/list/shopping")

    assert recipients(await received(app, push_transport)) == ["ewa", "ola"]


async def test_send_to_users_respects_preferences(app, login_as, push_transport):
    ala = await login_as("ala")
    ola = await login_as("ola")
    await subscribe(ala, "ala")
    await subscribe(ola, "ola")
    await set_preference(ola, "shopping_started", False)

    app.state.notifier.send_to_users(
        [await user_id(app, "ala"), await user_id(app, "ola")], notification()
    )

    assert recipients(await received(app, push_transport)) == ["ala"]


async def test_type_disabled_by_default_needs_explicit_opt_in(
    app, login_as, push_transport, monkeypatch
):
    # Przyszły typ domyślnie wyłączony (np. przypomnienia #40) — bez migracji, tylko w kodzie.
    monkeypatch.setitem(preferences.DEFAULT_ENABLED, NotificationType.ITEMS_ADDED, False)
    ala = await login_as("ala")
    ola = await login_as("ola")
    await subscribe(ala, "ala")
    await subscribe(ola, "ola")
    await set_preference(ola, "items_added", True)

    app.state.notifier.send_to_users(
        [await user_id(app, "ala"), await user_id(app, "ola")],
        notification(type=NotificationType.ITEMS_ADDED),
    )

    assert recipients(await received(app, push_transport)) == ["ola"]
    types = (await ala.get("/api/push/preferences")).json()["types"]
    assert {"type": "items_added", "enabled": False} in types

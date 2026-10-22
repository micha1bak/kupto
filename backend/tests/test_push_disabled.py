"""Bez kluczy VAPID (domyślne ustawienia testów) powiadomienia są wyłączone, a aplikacja działa."""

import logging

from kupto.push.notification import Notification, NotificationType


async def test_public_key_is_not_available(login_as):
    ala = await login_as("ala")

    response = await ala.get("/api/push/public-key")

    assert response.status_code == 404
    assert response.json()["code"] == "push_disabled"


async def test_subscribing_is_not_available_but_deleting_is_harmless(login_as):
    ala = await login_as("ala")
    body = {
        "endpoint": "https://fcm.googleapis.com/fcm/send/x",
        "keys": {"p256dh": "B" + "A" * 86, "auth": "A" * 22},
    }

    put = await ala.put("/api/push/subscriptions", json=body)
    delete = await ala.request("DELETE", "/api/push/subscriptions", json={"endpoint": "x"})

    assert put.status_code == 404
    assert put.json()["code"] == "push_disabled"
    assert delete.status_code == 204


async def test_sending_is_a_logged_no_op(app, household_with, caplog):
    ala, ola = await household_with("ala", "ola")
    household_id = (await ala.get("/api/households/me")).json()["id"]
    notification = Notification(NotificationType.SHOPPING_STARTED, "Zakupy", "ala idzie")

    with caplog.at_level(logging.INFO, logger="kupto.push.notifier"):
        app.state.notifier.send_to_household(household_id, notification)
        app.state.notifier.send_to_users([1, 2], notification)
        await app.state.notifier.drain()

    assert not app.state.notifier.enabled
    assert "wyłączone" in caplog.text
    # Reszta aplikacji działa normalnie.
    assert (await ola.post("/api/list/needs", json={"name": "mleko"})).status_code == 201

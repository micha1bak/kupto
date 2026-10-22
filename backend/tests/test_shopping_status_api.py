from datetime import datetime, timedelta

from sqlalchemy import update

from kupto.models import User


def shopper_logins(body):
    return [s["login"] for s in body["shoppers"]]


async def test_list_has_no_shoppers_by_default(household_with):
    (ala,) = await household_with("ala")

    assert (await ala.get("/api/list")).json()["shoppers"] == []


async def test_start_is_visible_to_household_members(household_with):
    ala, ola = await household_with("ala", "ola")
    (ewa,) = await household_with("ewa", name="Inny dom")

    response = await ala.post("/api/list/shopping")

    assert response.status_code == 200
    (shopper,) = response.json()["shoppers"]
    assert shopper["login"] == "ala"
    since = datetime.fromisoformat(shopper["since"])
    assert datetime.fromisoformat(shopper["expires_at"]) - since == timedelta(hours=3)
    assert shopper_logins((await ola.get("/api/list")).json()) == ["ala"]
    assert (await ewa.get("/api/list")).json()["shoppers"] == []


async def test_repeated_start_keeps_since(household_with):
    (ala,) = await household_with("ala")
    first = (await ala.post("/api/list/shopping")).json()["shoppers"]

    second = (await ala.post("/api/list/shopping")).json()["shoppers"]

    assert second == first


async def test_stop_removes_status_and_keeps_items(household_with):
    ala, ola = await household_with("ala", "ola")
    await ala.post("/api/list/needs", json={"name": "mleko"})
    await ala.post("/api/list/shopping")
    await ola.post("/api/list/shopping")

    body = (await ala.delete("/api/list/shopping")).json()

    assert shopper_logins(body) == ["ola"]
    assert [i["name"] for g in body["groups"] for i in g["items"]] == ["mleko"]
    # Ponowne wyłączenie nie jest błędem.
    assert (await ala.delete("/api/list/shopping")).status_code == 200


async def test_finish_shopping_clears_finishers_status(household_with):
    ala, ola = await household_with("ala", "ola")
    await ala.post("/api/list/shopping")
    await ola.post("/api/list/shopping")

    body = (await ala.post("/api/list/finish")).json()

    assert shopper_logins(body) == ["ola"]


async def test_expired_status_is_not_shown(household_with, session):
    (ala,) = await household_with("ala")
    await ala.post("/api/list/shopping")
    await session.execute(
        update(User).values(shopping_since=User.shopping_since - timedelta(hours=3, minutes=1))
    )
    await session.commit()

    assert (await ala.get("/api/list")).json()["shoppers"] == []
    assert shopper_logins((await ala.post("/api/list/shopping")).json()) == ["ala"]


async def test_status_requires_household(login_as):
    ala = await login_as("ala")

    assert (await ala.post("/api/list/shopping")).status_code == 409


async def test_status_requires_login(client):
    assert (await client.post("/api/list/shopping")).status_code == 401
    assert (await client.delete("/api/list/shopping")).status_code == 401

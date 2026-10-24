import pytest
from sqlalchemy import update

from kupto.auth.security import SESSION_COOKIE
from kupto.models import User


async def test_register_creates_account(client):
    response = await client.post(
        "/api/auth/register", json={"login": "ala", "password": "haslo1234", "name": "Ala"}
    )

    assert response.status_code == 201


async def test_register_rejects_taken_login(client):
    await client.post(
        "/api/auth/register", json={"login": "ala", "password": "haslo1234", "name": "Ala"}
    )

    response = await client.post(
        "/api/auth/register", json={"login": "ala", "password": "inne-haslo", "name": "Ala"}
    )

    assert response.status_code == 409


@pytest.mark.parametrize(
    "payload, field",
    [
        ({"login": "al", "password": "haslo1234", "name": "Ala"}, "login"),
        ({"login": "a" * 51, "password": "haslo1234", "name": "Ala"}, "login"),
        ({"login": "ala", "password": "krotkie", "name": "Ala"}, "password"),
        ({"login": "ala", "password": "haslo1234"}, "name"),
        ({"login": "ala", "password": "haslo1234", "name": "   "}, "name"),
        ({"login": "ala", "password": "haslo1234", "name": "A" * 41}, "name"),
    ],
)
async def test_register_rejects_invalid_data(client, payload, field):
    response = await client.post("/api/auth/register", json=payload)

    assert response.status_code == 422
    assert [e["loc"][-1] for e in response.json()["detail"]] == [field]


async def test_password_is_not_stored_in_plain_text(client, session):
    from sqlalchemy import select

    from kupto.models import User

    await client.post(
        "/api/auth/register", json={"login": "ala", "password": "haslo1234", "name": "Ala"}
    )

    user = await session.scalar(select(User).where(User.login == "ala"))
    assert user.password_hash != "haslo1234"


async def test_login_sets_httponly_session_cookie(client):
    await client.post(
        "/api/auth/register", json={"login": "ala", "password": "haslo1234", "name": "Ala"}
    )

    response = await client.post("/api/auth/login", json={"login": "ala", "password": "haslo1234"})

    assert response.status_code == 200
    set_cookie = response.headers["set-cookie"]
    assert set_cookie.startswith(f"{SESSION_COOKIE}=")
    assert "HttpOnly" in set_cookie
    assert "Max-Age=2592000" in set_cookie
    assert "SameSite=strict" in set_cookie


async def test_login_errors_are_indistinguishable(client):
    await client.post(
        "/api/auth/register", json={"login": "ala", "password": "haslo1234", "name": "Ala"}
    )

    wrong_password = await client.post(
        "/api/auth/login", json={"login": "ala", "password": "zle-haslo"}
    )
    unknown_login = await client.post(
        "/api/auth/login", json={"login": "nieznany", "password": "haslo1234"}
    )

    assert wrong_password.status_code == unknown_login.status_code == 401
    assert wrong_password.json() == unknown_login.json()


async def test_logout_ends_session(login_as):
    client = await login_as("ala")

    response = await client.post("/api/auth/logout")

    assert response.status_code == 200
    assert (await client.get("/api/users/me")).status_code == 401


async def test_protected_endpoint_requires_session(client):
    assert (await client.get("/api/users/me")).status_code == 401


async def test_forged_session_is_rejected(client):
    client.cookies.set(SESSION_COOKIE, "nie.jest.tokenem")

    assert (await client.get("/api/users/me")).status_code == 401


async def test_profile_without_household(login_as):
    client = await login_as("ala")

    response = await client.get("/api/users/me")

    assert response.status_code == 200
    assert response.json()["login"] == "ala"
    assert response.json()["household"] is None


async def test_register_stores_trimmed_name_shown_in_profile(client):
    await client.post(
        "/api/auth/register", json={"login": "ala", "password": "haslo1234", "name": "  Ala  "}
    )
    await client.post("/api/auth/login", json={"login": "ala", "password": "haslo1234"})

    assert (await client.get("/api/users/me")).json()["name"] == "Ala"


async def test_name_can_be_changed(login_as):
    client = await login_as("ala", name="Ala")

    response = await client.patch("/api/users/me", json={"name": " Ala K. "})

    assert response.status_code == 200
    assert response.json()["name"] == "Ala K."
    assert (await client.get("/api/users/me")).json()["name"] == "Ala K."


@pytest.mark.parametrize("name", ["", "   ", "A" * 41])
async def test_invalid_name_change_is_rejected(login_as, name):
    client = await login_as("ala", name="Ala")

    response = await client.patch("/api/users/me", json={"name": name})

    assert response.status_code == 422
    assert (await client.get("/api/users/me")).json()["name"] == "Ala"


async def test_account_without_name_has_null_name_in_profile(login_as, session):
    client = await login_as("ala")
    # Konto sprzed czatu grupowego (#78) — migracja 0012 zostawia imię puste.
    await session.execute(update(User).values(name=None))
    await session.commit()

    assert (await client.get("/api/users/me")).json()["name"] is None

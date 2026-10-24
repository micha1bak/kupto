import pytest
from sqlalchemy import select, update

from kupto.auth.security import SESSION_COOKIE, hash_password
from kupto.models import User

ALA = {"email": "ala@example.com", "password": "haslo1234", "name": "Ala"}


async def register(client, **overrides):
    return await client.post("/api/auth/register", json=ALA | overrides)


async def test_register_creates_account(client):
    response = await register(client)

    assert response.status_code == 201


async def test_register_stores_lowercase_email_without_login(client, session):
    await register(client, email="  Ala@Example.COM ")

    user = await session.scalar(select(User))
    assert (user.email, user.login, user.email_verified_at) == ("ala@example.com", None, None)


@pytest.mark.parametrize("email", ["ala@example.com", "ALA@example.com", " Ala@Example.Com"])
async def test_register_rejects_taken_email_regardless_of_case(client, email):
    await register(client)

    response = await register(client, email=email, password="inne-haslo")

    assert response.status_code == 409
    assert "adresem" in response.json()["detail"]


@pytest.mark.parametrize(
    "payload, field",
    [
        ({"email": "ala", "password": "haslo1234", "name": "Ala"}, "email"),
        ({"email": "ala@", "password": "haslo1234", "name": "Ala"}, "email"),
        ({"email": "ala@example", "password": "haslo1234", "name": "Ala"}, "email"),
        ({"email": "a la@example.com", "password": "haslo1234", "name": "Ala"}, "email"),
        ({"email": "ala@@example.com", "password": "haslo1234", "name": "Ala"}, "email"),
        ({"email": "a" * 65 + "@example.com", "password": "haslo1234", "name": "Ala"}, "email"),
        ({"email": "a@" + "b" * 250 + ".pl", "password": "haslo1234", "name": "Ala"}, "email"),
        ({"login": "ala", "password": "haslo1234", "name": "Ala"}, "email"),
        ({"email": "ala@example.com", "password": "krotkie", "name": "Ala"}, "password"),
        ({"email": "ala@example.com", "password": "haslo1234"}, "name"),
        ({"email": "ala@example.com", "password": "haslo1234", "name": "   "}, "name"),
        ({"email": "ala@example.com", "password": "haslo1234", "name": "A" * 41}, "name"),
    ],
)
async def test_register_rejects_invalid_data(client, payload, field):
    response = await client.post("/api/auth/register", json=payload)

    assert response.status_code == 422
    assert [e["loc"][-1] for e in response.json()["detail"]] == [field]


@pytest.mark.parametrize(
    "email", ["ala.kowalska+zakupy@poczta.example.pl", "o'neil@xn--d1acj3b.pl"]
)
async def test_register_accepts_unusual_but_valid_email(client, email):
    assert (await register(client, email=email)).status_code == 201


async def test_password_is_not_stored_in_plain_text(client, session):
    await register(client)

    user = await session.scalar(select(User).where(User.email == "ala@example.com"))
    assert user.password_hash != "haslo1234"


async def test_login_sets_httponly_session_cookie(client):
    await register(client)

    response = await client.post(
        "/api/auth/login", json={"email": "ala@example.com", "password": "haslo1234"}
    )

    assert response.status_code == 200
    set_cookie = response.headers["set-cookie"]
    assert set_cookie.startswith(f"{SESSION_COOKIE}=")
    assert "HttpOnly" in set_cookie
    assert "Max-Age=2592000" in set_cookie
    assert "SameSite=strict" in set_cookie


async def test_login_with_email_ignores_case(client):
    await register(client)

    response = await client.post(
        "/api/auth/login", json={"email": " ALA@example.com", "password": "haslo1234"}
    )

    assert response.status_code == 200


async def test_login_accepts_legacy_login_field_with_email(client):
    # Stara wersja PWA w cache wysyła pole `login`.
    await register(client)

    response = await client.post(
        "/api/auth/login", json={"login": "ala@example.com", "password": "haslo1234"}
    )

    assert response.status_code == 200


async def test_login_errors_are_indistinguishable(client):
    await register(client)

    wrong_password = await client.post(
        "/api/auth/login", json={"email": "ala@example.com", "password": "zle-haslo"}
    )
    unknown_email = await client.post(
        "/api/auth/login", json={"email": "nieznany@example.com", "password": "haslo1234"}
    )

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


async def legacy_account(session, login="stary", name="Stary", password="haslo1234") -> User:
    """Konto sprzed #77: login bez adresu e-mail (stan po migracji 0013)."""
    user = User(login=login, name=name, password_hash=hash_password(password))
    session.add(user)
    await session.commit()
    return user


async def test_legacy_account_logs_in_with_login(client, session):
    await legacy_account(session)

    response = await client.post(
        "/api/auth/login", json={"login": "stary", "password": "haslo1234"}
    )

    assert response.status_code == 200
    profile = (await client.get("/api/users/me")).json()
    assert (profile["login"], profile["email"], profile["email_status"]) == (
        "stary",
        None,
        "missing",
    )


async def test_login_is_case_sensitive_like_before(client, session):
    await legacy_account(session)

    response = await client.post(
        "/api/auth/login", json={"email": "STARY", "password": "haslo1234"}
    )

    assert response.status_code == 401


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
    profile = response.json()
    assert profile["login"] is None
    assert profile["email"] == "ala@example.com"
    assert profile["email_verified"] is False
    assert profile["email_status"] == "unverified"
    # Bez wysyłki link nie wyszedł, więc termin potwierdzenia nie biegnie.
    assert profile["verify_email_by"] is None
    # Wysyłka niedostępna (domyślny fixture) — nikt nie jest blokowany.
    assert (profile["mail_enabled"], profile["email_blocked"]) == (False, False)
    assert profile["household"] is None


async def test_auth_config_reports_mail_availability(client):
    assert (await client.get("/api/auth/config")).json() == {"mail_enabled": False}


async def test_register_stores_trimmed_name_shown_in_profile(client):
    await register(client, name="  Ala  ")
    await client.post("/api/auth/login", json={"email": "ala@example.com", "password": "haslo1234"})

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

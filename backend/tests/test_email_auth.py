"""Weryfikacja adresu, adres w starych kontach, reset hasła i limity prób (#77)."""

import asyncio
from datetime import datetime, timedelta

import jwt
import pytest
from sqlalchemy import select, text, update

from kupto.auth import rate_limit
from kupto.auth.security import SESSION_COOKIE, hash_password
from kupto.auth.tokens import token_hash
from kupto.db import utcnow
from kupto.models import AuthRateEvent, AuthToken, User

PASSWORD = "haslo-testowe"


@pytest.fixture
def mail_delivers() -> bool:
    # Wysyłka działa (SES albo dev z linkami w logu) — weryfikacja adresów jest wymagana.
    return True


async def login(client, identifier: str, password: str = PASSWORD):
    return await client.post("/api/auth/login", json={"email": identifier, "password": password})


async def profile(client) -> dict:
    return (await client.get("/api/users/me")).json()


async def verify(client, token: str):
    return await client.post("/api/auth/verify-email", json={"token": token})


async def legacy_account(session, login="stary", name="Stary") -> User:
    """Konto sprzed #77: login bez adresu e-mail (stan po migracji 0013)."""
    user = User(login=login, name=name, password_hash=hash_password(PASSWORD))
    session.add(user)
    await session.commit()
    return user


async def expire_deadline(session, email_or_login: str) -> None:
    await session.execute(
        update(User)
        .where((User.email == email_or_login) | (User.login == email_or_login))
        .values(verify_email_by=utcnow() - timedelta(minutes=1))
    )
    await session.commit()


# --- Rejestracja i weryfikacja ---


async def test_registration_sends_verification_link_and_stores_only_hash(login_as, mail, session):
    await login_as("ala")

    (message,) = mail.sent
    assert message.to == "ala@example.com"
    assert "http://localhost:5173/verify-email#token=" in message.body
    token = mail.last_token()
    stored = (await session.execute(text("SELECT token_hash FROM auth_tokens"))).scalars().all()
    assert stored == [token_hash(token)]
    assert token not in str(stored)


async def test_valid_link_verifies_address_without_session(login_as, mail, client):
    ala = await login_as("ala")

    # Link otwarty na innym urządzeniu — bez sesji.
    response = await verify(client, mail.last_token())

    assert response.status_code == 200
    me = await profile(ala)
    assert (me["email"], me["email_verified"], me["email_status"]) == (
        "ala@example.com",
        True,
        "verified",
    )
    assert me["verify_email_by"] is None


async def test_expired_link_is_rejected(login_as, mail, client, session):
    ala = await login_as("ala")
    await session.execute(update(AuthToken).values(expires_at=utcnow() - timedelta(seconds=1)))
    await session.commit()

    response = await verify(client, mail.last_token())

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_token"
    assert (await profile(ala))["email_verified"] is False


async def test_link_works_only_once(login_as, mail, client):
    await login_as("ala")
    token = mail.last_token()

    assert (await verify(client, token)).status_code == 200
    second = await verify(client, token)

    assert second.status_code == 400
    assert second.json()["code"] == "invalid_token"


@pytest.mark.parametrize("token", ["", "nie-ma-takiego", "x" * 300])
async def test_unknown_link_is_rejected(client, token):
    response = await verify(client, token)

    assert response.status_code in (400, 422)


async def test_resend_invalidates_previous_link(login_as, mail, client):
    ala = await login_as("ala")
    first = mail.last_token()

    response = await ala.post("/api/users/me/email", json={"email": "ala@example.com"})

    assert response.status_code == 200
    assert len(mail.sent) == 2
    assert (await verify(client, first)).status_code == 400
    assert (await verify(client, mail.last_token())).status_code == 200


async def test_unverified_address_can_be_corrected_before_confirmation(login_as, mail, client):
    ala = await login_as("ala")

    response = await ala.post("/api/users/me/email", json={"email": "Ala.Nowa@example.com"})

    assert response.json()["email"] == "ala.nowa@example.com"
    # Do kliknięcia logowanie dotychczasowym adresem.
    assert (await login(client, "ala@example.com")).status_code == 200
    assert (await verify(client, mail.last_token("ala.nowa@example.com"))).status_code == 200
    assert (await login(client, "ala.nowa@example.com")).status_code == 200
    assert (await login(client, "ala@example.com")).status_code == 401


async def test_verified_address_cannot_be_changed_here(login_as, mail, client):
    ala = await login_as("ala")
    await verify(client, mail.last_token())

    response = await ala.post("/api/users/me/email", json={"email": "inny@example.com"})

    assert response.status_code == 409


async def test_address_of_another_account_is_rejected(login_as):
    await login_as("ola")
    ala = await login_as("ala")

    response = await ala.post("/api/users/me/email", json={"email": "OLA@example.com"})

    assert response.status_code == 409


# --- Termin potwierdzenia ---


async def test_unverified_account_works_before_deadline(household_with):
    (ala,) = await household_with("ala")

    me = await profile(ala)
    assert (me["email_status"], me["email_blocked"]) == ("unverified", False)
    assert (await ala.get("/api/list")).status_code == 200


async def test_household_is_blocked_after_deadline_until_verified(
    household_with, session, mail, client
):
    (ala,) = await household_with("ala")
    await expire_deadline(session, "ala@example.com")

    response = await ala.get("/api/list")

    assert response.status_code == 403
    assert response.json()["code"] == "email_unverified"
    me = await profile(ala)
    assert me["email_blocked"] is True
    # Ponowne wysłanie linku działa, a termin się nie przesuwa.
    assert (await ala.post("/api/users/me/email", json={"email": "ala@example.com"})).is_success
    assert (await profile(ala))["email_blocked"] is True

    await verify(client, mail.last_token())

    assert (await ala.get("/api/list")).status_code == 200
    assert (await profile(ala))["email_blocked"] is False


@pytest.mark.parametrize("mail_delivers", [False])
async def test_nobody_is_blocked_without_mail_delivery(household_with, session):
    (ala,) = await household_with("ala")
    await expire_deadline(session, "ala@example.com")

    assert (await ala.get("/api/list")).status_code == 200
    me = await profile(ala)
    assert (me["mail_enabled"], me["email_blocked"]) == (False, False)


@pytest.mark.parametrize("mail_delivers", [False])
async def test_mail_requests_are_unavailable_without_delivery(login_as, client, mail):
    ala = await login_as("ala")

    resend = await ala.post("/api/users/me/email", json={"email": "ala@example.com"})
    reset = await client.post("/api/auth/password-reset", json={"email": "ala@example.com"})
    unknown = await client.post("/api/auth/password-reset", json={"email": "nikt@example.com"})

    assert resend.status_code == reset.status_code == unknown.status_code == 503
    assert reset.json() == unknown.json()
    assert reset.json()["code"] == "mail_unavailable"
    assert (await client.get("/api/auth/config")).json() == {"mail_enabled": False}


# --- Konta sprzed #77 ---


async def test_legacy_account_must_provide_email(make_client, session):
    await legacy_account(session)
    client = make_client()
    assert (await login(client, "stary")).status_code == 200

    me = await profile(client)
    assert (me["email_status"], me["email_blocked"]) == ("missing", True)
    response = await client.post("/api/households", json={"name": "Dom"})
    assert response.status_code == 201  # tworzenie gospodarstwa nie jest blokowane
    blocked = await client.get("/api/households/me")
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "email_required"


async def test_legacy_account_switches_to_email_after_verification(make_client, session, mail):
    await legacy_account(session)
    client = make_client()
    await login(client, "stary")

    response = await client.post("/api/users/me/email", json={"email": "Stary@Example.com"})

    assert response.status_code == 200
    me = response.json()
    assert (me["email"], me["email_status"], me["email_blocked"]) == (
        "stary@example.com",
        "unverified",
        False,
    )
    (message,) = mail.sent
    assert "zamiast dotychczasowego loginu" in message.body
    # Adres czeka w tokenie: nie służy jeszcze do logowania, login działa dalej.
    assert (await session.scalar(select(User.email).where(User.login == "stary"))) is None
    other = make_client()
    assert (await login(other, "stary@example.com")).status_code == 401
    assert (await login(other, "stary")).status_code == 200

    confirmed = await verify(other, mail.last_token())

    assert "logujesz się adresem" in confirmed.json()["message"]
    assert (await login(other, "stary")).status_code == 401
    assert (await login(other, "STARY@example.com")).status_code == 200
    assert (await profile(other))["login"] == "stary"


async def test_pending_address_of_legacy_account_gets_no_reset_link(make_client, session, mail):
    await legacy_account(session)
    client = make_client()
    await login(client, "stary")
    await client.post("/api/users/me/email", json={"email": "stary@example.com"})

    response = await make_client().post(
        "/api/auth/password-reset", json={"email": "stary@example.com"}
    )

    assert response.status_code == 202
    assert [m.kind for m in mail.sent] == ["verify_email"]


async def test_legacy_verification_fails_when_address_was_taken(
    make_client, login_as, session, mail
):
    await legacy_account(session)
    client = make_client()
    await login(client, "stary")
    await client.post("/api/users/me/email", json={"email": "wspolny@example.com"})
    legacy_token = mail.last_token()
    # W międzyczasie ktoś inny rejestruje ten adres.
    await make_client().post(
        "/api/auth/register",
        json={"email": "wspolny@example.com", "password": PASSWORD, "name": "Ktoś"},
    )

    response = await verify(client, legacy_token)

    assert response.status_code == 409
    assert (await login(make_client(), "stary")).status_code == 200


# --- Reset hasła ---


async def request_reset(client, email: str):
    return await client.post("/api/auth/password-reset", json={"email": email})


async def confirm_reset(client, token: str, password: str = "nowe-haslo-1"):
    return await client.post(
        "/api/auth/password-reset/confirm", json={"token": token, "password": password}
    )


async def test_reset_request_does_not_reveal_whether_account_exists(login_as, mail, make_client):
    await login_as("ala")
    mail.sent.clear()

    existing = await request_reset(make_client(), "ALA@example.com")
    missing = await request_reset(make_client(), "nikt@example.com")

    assert existing.status_code == missing.status_code == 202
    assert existing.json() == missing.json()
    (message,) = mail.sent
    assert message.to == "ala@example.com"
    assert "http://localhost:5173/reset-password#token=" in message.body


def backdate_session(client, user_id: int, settings, seconds: int = 10) -> None:
    """Sesja wydana kilka sekund temu (`iat` ma dokładność sekundy)."""
    issued = utcnow() - timedelta(seconds=seconds)
    token = jwt.encode(
        {"sub": str(user_id), "iat": issued, "exp": issued + timedelta(days=30)},
        settings.jwt_secret,
        algorithm="HS256",
    )
    client.cookies.set(SESSION_COOKIE, token)


async def test_reset_sets_new_password_and_ends_old_sessions(login_as, mail, make_client, settings):
    phone = await login_as("ala")
    backdate_session(phone, (await profile(phone))["id"], settings)
    assert (await phone.get("/api/users/me")).status_code == 200
    browser = make_client()
    await request_reset(browser, "ala@example.com")

    response = await confirm_reset(browser, mail.last_token("ala@example.com"))

    assert response.status_code == 200
    assert (await phone.get("/api/users/me")).status_code == 401
    assert (await login(browser, "ala@example.com", PASSWORD)).status_code == 401
    assert (await login(browser, "ala@example.com", "nowe-haslo-1")).status_code == 200
    # Nowa sesja działa, a kliknięcie linku ze skrzynki potwierdziło adres.
    assert (await profile(browser))["email_verified"] is True


async def test_reset_link_works_only_once(login_as, mail, make_client):
    await login_as("ala")
    client = make_client()
    await request_reset(client, "ala@example.com")
    token = mail.last_token()
    assert (await confirm_reset(client, token)).status_code == 200

    second = await confirm_reset(client, token, "trzecie-haslo")

    assert second.status_code == 400
    assert second.json()["code"] == "invalid_token"
    assert (await login(client, "ala@example.com", "nowe-haslo-1")).status_code == 200


async def test_expired_reset_link_is_rejected(login_as, mail, make_client, session):
    await login_as("ala")
    client = make_client()
    await request_reset(client, "ala@example.com")
    await session.execute(
        update(AuthToken)
        .where(AuthToken.purpose == "reset_password")
        .values(expires_at=utcnow() - timedelta(seconds=1))
    )
    await session.commit()

    response = await confirm_reset(client, mail.last_token())

    assert response.status_code == 400
    assert (await login(client, "ala@example.com")).status_code == 200


async def test_new_reset_request_invalidates_previous_link(login_as, mail, make_client):
    await login_as("ala")
    client = make_client()
    await request_reset(client, "ala@example.com")
    first = mail.last_token()
    await request_reset(client, "ala@example.com")

    assert (await confirm_reset(client, first)).status_code == 400
    assert (await confirm_reset(client, mail.last_token())).status_code == 200


async def test_verification_link_is_not_a_reset_link(login_as, mail, make_client):
    await login_as("ala")

    response = await confirm_reset(make_client(), mail.last_token())

    assert response.status_code == 400


async def test_reset_rejects_short_password(login_as, mail, make_client):
    await login_as("ala")
    client = make_client()
    await request_reset(client, "ala@example.com")

    response = await confirm_reset(client, mail.last_token(), "krotkie")

    assert response.status_code == 422
    # Token nie został zużyty przez błędne dane.
    assert (await confirm_reset(client, mail.last_token())).status_code == 200


# --- Limity prób ---


async def test_reset_requests_are_limited_per_address_regardless_of_account(
    login_as, mail, make_client
):
    await login_as("ala")
    mail.sent.clear()
    for email in ("ala@example.com", "nikt@example.com"):
        for _ in range(3):
            assert (await request_reset(make_client(), email)).status_code == 202

        response = await request_reset(make_client(), email)

        assert response.status_code == 429
        assert int(response.headers["Retry-After"]) > 0
    assert len(mail.sent) == 3


async def test_reset_requests_are_limited_per_ip(make_client):
    client = make_client(ip="192.0.2.7")
    for n in range(10):
        assert (await request_reset(client, f"osoba{n}@example.com")).status_code == 202

    assert (await request_reset(client, "osoba10@example.com")).status_code == 429


async def test_registrations_are_limited_per_ip(make_client, session):
    def payload(n: int) -> dict:
        return {"email": f"konto{n}@example.com", "password": PASSWORD, "name": "Konto"}

    for n in range(5):
        response = await make_client(ip="192.0.2.8").post("/api/auth/register", json=payload(n))
        assert response.status_code == 201

    response = await make_client(ip="192.0.2.8").post("/api/auth/register", json=payload(5))

    assert response.status_code == 429
    assert "Retry-After" in response.headers
    assert await session.scalar(select(User).where(User.email == "konto5@example.com")) is None
    other_ip = await make_client(ip="192.0.2.9").post("/api/auth/register", json=payload(5))
    assert other_ip.status_code == 201


async def test_verification_resends_are_limited(login_as, mail):
    ala = await login_as("ala")  # rejestracja wysłała już pierwszy link (poza limitem)
    for _ in range(3):
        assert (
            await ala.post("/api/users/me/email", json={"email": "ala@example.com"})
        ).status_code == 200

    response = await ala.post("/api/users/me/email", json={"email": "ala@example.com"})

    assert response.status_code == 429
    assert len(mail.sent) == 4


async def test_rate_limit_stores_no_plain_addresses(make_client, session):
    await request_reset(make_client(ip="192.0.2.10"), "tajny@example.com")

    rows = (await session.execute(text("SELECT action, key_hash FROM auth_rate_events"))).all()

    assert {action for action, _ in rows} == {"password_reset_email", "password_reset_ip"}
    assert not any("tajny" in key or "192.0.2" in key for _, key in rows)


# --- Domownicy ---


async def test_member_can_be_added_only_by_verified_address(household_with, login_as, mail):
    (ala,) = await household_with("ala")
    await login_as("ola")
    ola_token = mail.last_token("ola@example.com")

    unverified = await ala.post("/api/households/me/members", json={"email": "ola@example.com"})
    assert unverified.status_code == 404

    await verify(ala, ola_token)
    response = await ala.post("/api/households/me/members", json={"email": "OLA@example.com"})

    assert response.status_code == 201
    assert [m["name"] for m in response.json()["members"]] == ["ala", "ola"]


async def test_legacy_member_can_be_added_by_login(household_with, session):
    (ala,) = await household_with("ala")
    await legacy_account(session)

    response = await ala.post("/api/households/me/members", json={"login": "stary"})

    assert response.status_code == 201
    assert [m["name"] for m in response.json()["members"]] == ["ala", "Stary"]


async def test_parallel_requests_do_not_exceed_limit(login_as, mail, make_client):
    await login_as("ala")
    mail.sent.clear()
    clients = [make_client() for _ in range(8)]  # osobne IP — liczy się limit na adres

    responses = await asyncio.gather(*(request_reset(c, "ala@example.com") for c in clients))

    assert sorted(r.status_code for r in responses) == [202] * 3 + [429] * 5
    assert len(mail.sent) == 3


async def test_old_rate_events_are_cleaned_up_occasionally(make_client, session, monkeypatch):
    monkeypatch.setattr(rate_limit, "CLEANUP_EVERY", 1)  # sprzątanie przy tym zapisie
    session.add(
        AuthRateEvent(
            action="register_ip", key_hash="0" * 64, created_at=utcnow() - timedelta(days=2)
        )
    )
    await session.commit()

    await request_reset(make_client(), "ktos@example.com")

    rows = (await session.execute(text("SELECT action FROM auth_rate_events"))).scalars().all()
    assert sorted(rows) == ["password_reset_email", "password_reset_ip"]


@pytest.mark.parametrize("mail_delivers", [False])
async def test_deadline_starts_with_first_sent_link(login_as, mail, session):
    """Konto założone przy MAIL_BACKEND=log nie jest blokowane od razu po włączeniu SES."""
    ala = await login_as("ala")
    assert (await profile(ala))["verify_email_by"] is None
    await session.execute(update(User).values(created_at=utcnow() - timedelta(days=8)))
    await session.commit()
    await ala.post("/api/households", json={"name": "Dom"})

    mail.delivers = True  # włączenie SES (MAIL_BACKEND=ses)

    me = await profile(ala)
    assert (me["email_status"], me["email_blocked"], me["verify_email_by"]) == (
        "unverified",
        False,
        None,
    )
    assert (await ala.get("/api/list")).status_code == 200

    response = await ala.post("/api/users/me/email", json={"email": "ala@example.com"})

    assert response.status_code == 200
    deadline = datetime.fromisoformat(response.json()["verify_email_by"])
    assert timedelta(days=6, hours=23) < deadline - utcnow() <= timedelta(days=7)
    assert mail.sent[-1].to == "ala@example.com"

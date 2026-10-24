from datetime import UTC, datetime, timedelta

import jwt
import pytest
from pydantic import ValidationError

from kupto.auth.security import (
    SessionClaims,
    create_session_token,
    hash_password,
    read_session_token,
    session_is_revoked,
    verify_password,
)
from kupto.config import Settings
from kupto.errors import Unauthorized

SETTINGS = Settings(jwt_secret="unit-test-secret-that-is-long-enough")


@pytest.mark.parametrize("secret", ["", "za-krotki-sekret"])
def test_empty_or_short_jwt_secret_is_rejected_at_startup(secret):
    with pytest.raises(ValidationError, match="jwt_secret"):
        Settings(jwt_secret=secret)


def test_password_is_hashed_and_verifiable():
    hashed = hash_password("tajne-haslo")

    assert hashed != "tajne-haslo"
    assert verify_password("tajne-haslo", hashed)
    assert not verify_password("inne-haslo", hashed)


def test_verify_without_hash_is_always_false():
    assert not verify_password("cokolwiek", None)


def test_valid_token_returns_user_id():
    assert read_session_token(create_session_token(42, SETTINGS), SETTINGS) == 42


def test_expired_token_is_rejected():
    past = datetime.now(UTC) - timedelta(days=31)
    token = jwt.encode(
        {"sub": "42", "iat": past, "exp": past + timedelta(days=30)},
        SETTINGS.jwt_secret,
        algorithm="HS256",
    )

    with pytest.raises(Unauthorized):
        read_session_token(token, SETTINGS)


def test_forged_token_is_rejected():
    token = create_session_token(42, Settings(jwt_secret="another-secret-that-is-long-enough"))

    with pytest.raises(Unauthorized):
        read_session_token(token, SETTINGS)


def test_token_without_issue_time_is_rejected():
    token = jwt.encode(
        {"sub": "42", "exp": datetime.now(UTC) + timedelta(days=1)},
        SETTINGS.jwt_secret,
        algorithm="HS256",
    )

    with pytest.raises(Unauthorized):
        read_session_token(token, SETTINGS)


@pytest.mark.parametrize(
    "issued_at, revoked",
    [(99, True), (100, False), (101, False)],
)
def test_sessions_issued_before_password_reset_are_revoked(issued_at, revoked):
    # Reset w chwili 100,7 s: `iat` ma dokładność sekundy, więc sesja z sekundy 100 przeżywa
    # (inaczej logowanie tuż po resecie mogłoby zostać odrzucone).
    reset_at = datetime.fromtimestamp(100.7, UTC)

    assert session_is_revoked(SessionClaims(42, issued_at), reset_at) is revoked
    assert session_is_revoked(SessionClaims(42, issued_at), None) is False

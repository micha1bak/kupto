import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from kupto.config import Settings
from kupto.errors import Unauthorized

SESSION_COOKIE = "kupto_session"
_ALGORITHM = "HS256"

_password_hash = PasswordHash.recommended()
# Hash weryfikowany przy nieistniejącym loginie, by czas odpowiedzi nie zdradzał istnienia konta.
_DUMMY_HASH = _password_hash.hash("kupto-dummy-password")


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if password_hash is None:
        _password_hash.verify(password, _DUMMY_HASH)
        return False
    return _password_hash.verify(password, password_hash)


def create_session_token(user_id: int, settings: Settings) -> str:
    now = datetime.now(UTC)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(days=settings.jwt_ttl_days)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


@dataclass(frozen=True)
class SessionClaims:
    user_id: int
    issued_at: int  # sekundy od epoki (`iat`) — do unieważniania sesji sprzed resetu hasła


def read_session(token: str, settings: Settings) -> SessionClaims:
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[_ALGORITHM], options={"require": ["iat"]}
        )
        return SessionClaims(user_id=int(payload["sub"]), issued_at=int(payload["iat"]))
    except (jwt.PyJWTError, KeyError, ValueError, TypeError) as exc:
        raise Unauthorized("Sesja jest nieprawidłowa lub wygasła.") from exc


def read_session_token(token: str, settings: Settings) -> int:
    return read_session(token, settings).user_id


def session_is_revoked(claims: SessionClaims, valid_after: datetime | None) -> bool:
    """Czy sesję wydano przed `valid_after` (reset hasła). `iat` ma dokładność sekundy, więc
    sesja z tej samej sekundy co reset przeżywa — inaczej nowe logowanie zaraz po resecie
    mogłoby zostać odrzucone."""
    return valid_after is not None and claims.issued_at < math.floor(valid_after.timestamp())

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


def read_session_token(token: str, settings: Settings) -> int:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise Unauthorized("Sesja jest nieprawidłowa lub wygasła.") from exc

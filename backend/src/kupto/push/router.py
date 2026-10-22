import binascii
from typing import Annotated

from fastapi import APIRouter, Header, status
from pydantic import AfterValidator, BaseModel, Field

from kupto.deps import CurrentUser, NotifierDep, SessionDep
from kupto.errors import NotFound
from kupto.push import subscriptions
from kupto.push.keys import b64url_decode
from kupto.push.notifier import Notifier

router = APIRouter(prefix="/api/push", tags=["push"])

PUSH_DISABLED = "push_disabled"

B64URL = r"^[A-Za-z0-9_-]+={0,2}$"


def _decoded_length(expected: int, starts_with: bytes = b""):
    def check(value: str) -> str:
        try:
            raw = b64url_decode(value.rstrip("="))
        except (binascii.Error, ValueError) as exc:
            raise ValueError("Nieprawidłowy klucz subskrypcji.") from exc
        if len(raw) != expected or not raw.startswith(starts_with):
            raise ValueError("Nieprawidłowy klucz subskrypcji.")
        return value

    return AfterValidator(check)


Endpoint = Annotated[
    str,
    Field(max_length=subscriptions.MAX_ENDPOINT_LENGTH),
    AfterValidator(subscriptions.validate_endpoint),
]


class SubscriptionKeys(BaseModel):
    # Klucz publiczny ECDH urządzenia (nieskompresowany punkt P-256) i sekret uwierzytelniania.
    p256dh: Annotated[str, Field(max_length=200, pattern=B64URL), _decoded_length(65, b"\x04")]
    auth: Annotated[str, Field(max_length=100, pattern=B64URL), _decoded_length(16)]


class SubscriptionIn(BaseModel):
    """Kształt `PushSubscription.toJSON()` z przeglądarki (pole `expirationTime` pomijane)."""

    endpoint: Endpoint
    keys: SubscriptionKeys


class SubscriptionRef(BaseModel):
    endpoint: str = Field(max_length=subscriptions.MAX_ENDPOINT_LENGTH)


class PublicKeyOut(BaseModel):
    public_key: str


def _require_enabled(notifier: Notifier) -> str:
    if not notifier.enabled or notifier.public_key is None:
        raise NotFound("Powiadomienia są wyłączone na serwerze.", code=PUSH_DISABLED)
    return notifier.public_key


@router.get("/public-key")
async def public_key(_: CurrentUser, notifier: NotifierDep) -> PublicKeyOut:
    return PublicKeyOut(public_key=_require_enabled(notifier))


@router.put("/subscriptions", status_code=status.HTTP_204_NO_CONTENT)
async def save_subscription(
    payload: SubscriptionIn,
    user: CurrentUser,
    session: SessionDep,
    notifier: NotifierDep,
    user_agent: Annotated[str | None, Header()] = None,
) -> None:
    _require_enabled(notifier)
    await subscriptions.save(
        session,
        user,
        endpoint=payload.endpoint,
        p256dh=payload.keys.p256dh,
        auth=payload.keys.auth,
        user_agent=user_agent,
    )


@router.delete("/subscriptions", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    payload: SubscriptionRef, user: CurrentUser, session: SessionDep
) -> None:
    # Idempotentnie i także przy wyłączonych powiadomieniach — klient sprząta przy wylogowaniu.
    await subscriptions.remove(session, user, payload.endpoint)

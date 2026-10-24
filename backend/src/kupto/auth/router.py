from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Request, Response, status
from pydantic import AliasChoices, BaseModel, Field, StringConstraints
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from kupto.auth import accounts, emails, rate_limit, tokens
from kupto.auth.accounts import Email
from kupto.auth.security import (
    SESSION_COOKIE,
    create_session_token,
    hash_password,
    verify_password,
)
from kupto.db import utcnow
from kupto.deps import CurrentUser, MailDep, SessionDep, SettingsDep
from kupto.errors import Conflict, DomainError, Unauthorized
from kupto.mail import EmailMessage, MailSender, send_safely
from kupto.models import AuthToken, Household, User, display_name

router = APIRouter(prefix="/api", tags=["auth"])

INVALID_TOKEN = "invalid_token"
MAIL_UNAVAILABLE = "mail_unavailable"


class ServiceUnavailable(DomainError):
    status_code = 503


class InvalidToken(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "Link jest nieprawidłowy, wygasł albo został już użyty. Poproś o nowy.",
            code=INVALID_TOKEN,
        )


# Imię pokazywane domownikom w czacie i powiadomieniach (#78); spacje z brzegów są obcinane.
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
Password = Annotated[str, Field(min_length=8, max_length=128)]


class Registration(BaseModel):
    email: Email
    password: Password
    name: Name


class ProfileUpdate(BaseModel):
    name: Name


class LoginCredentials(BaseModel):
    # Adres albo — w koncie sprzed #77 bez potwierdzonego adresu — login. Stare wersje PWA
    # wysyłają pole `login`. Bez reguł formatu: każdy błąd danych ma dawać jednakowe 401.
    email: str = Field(max_length=300, validation_alias=AliasChoices("email", "login"))
    password: str = Field(max_length=200)


class EmailIn(BaseModel):
    email: Email


class TokenIn(BaseModel):
    token: str = Field(max_length=200)


class PasswordResetConfirm(BaseModel):
    token: str = Field(max_length=200)
    password: Password


class Message(BaseModel):
    message: str


class AuthConfig(BaseModel):
    mail_enabled: bool


class HouseholdRef(BaseModel):
    id: int
    name: str


class Profile(BaseModel):
    id: int
    # Tylko w kontach sprzed #77 — nowe konta logują się adresem.
    login: str | None
    name: str | None  # None w koncie sprzed czatu grupowego — klient prosi o uzupełnienie
    # Adres konta, a gdy go brak — adres czekający na potwierdzenie (konto sprzed #77).
    email: str | None
    email_verified: bool
    email_status: accounts.EmailStatus
    verify_email_by: datetime | None
    # Czy funkcje gospodarstwa są zablokowane do podania/potwierdzenia adresu.
    email_blocked: bool
    mail_enabled: bool
    household: HouseholdRef | None


def _client_ip(request: Request) -> str:
    # Za Caddy i nginx: uvicorn z --proxy-headers ustawia adres klienta (design D5).
    return request.client.host if request.client else "unknown"


def _require_mail(mail: MailSender) -> None:
    if not mail.delivers:
        raise ServiceUnavailable(
            "Wysyłka e-maili jest chwilowo niedostępna. Spróbuj później.", code=MAIL_UNAVAILABLE
        )


def _send_later(background: BackgroundTasks, mail: MailSender, message: EmailMessage) -> None:
    # Po wysłaniu odpowiedzi: czas odpowiedzi nie zależy od SES ani od istnienia konta.
    background.add_task(send_safely, mail, message)


async def _start_verification(
    session: SessionDep,
    settings: SettingsDep,
    mail: MailSender,
    background: BackgroundTasks,
    user: User,
    email: str,
) -> None:
    """Wystawia link weryfikacyjny (unieważnia poprzedni) i zatwierdza zapis; termin
    potwierdzenia liczy się od pierwszego podania adresu i nie przesuwa przy ponownym wysłaniu."""
    if user.verify_email_by is None:
        user.verify_email_by = utcnow() + timedelta(days=settings.email_verification_grace_days)
    token = await tokens.issue(
        session,
        user,
        tokens.VERIFY_EMAIL,
        email,
        timedelta(hours=settings.email_verification_ttl_hours),
    )
    await session.commit()
    message = emails.verification_message(
        settings, email, token, display_name(user), has_login=user.login is not None
    )
    _send_later(background, mail, message)


@router.get("/auth/config")
async def auth_config(mail: MailDep) -> AuthConfig:
    return AuthConfig(mail_enabled=mail.delivers)


@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
async def register(
    payload: Registration,
    request: Request,
    background: BackgroundTasks,
    session: SessionDep,
    settings: SettingsDep,
    mail: MailDep,
) -> Message:
    await rate_limit.check(session, (rate_limit.REGISTER_PER_IP, _client_ip(request)))
    user = User(
        email=payload.email,
        name=payload.name,
        password_hash=hash_password(payload.password),
        created_at=utcnow(),
    )
    session.add(user)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise Conflict("Konto z tym adresem e-mail już istnieje.") from exc
    await _start_verification(session, settings, mail, background, user, payload.email)
    return Message(message="Konto zostało utworzone.")


@router.post("/auth/login")
async def login(
    credentials: LoginCredentials, response: Response, session: SessionDep, settings: SettingsDep
) -> Message:
    user = await accounts.find_by_identifier(session, credentials.email)
    if not verify_password(credentials.password, user.password_hash if user else None):
        raise Unauthorized("Nieprawidłowy e-mail lub hasło.")
    assert user is not None
    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(user.id, settings),
        max_age=settings.jwt_ttl_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
    )
    return Message(message="Zalogowano.")


@router.post("/auth/logout")
async def logout(response: Response, settings: SettingsDep) -> Message:
    response.delete_cookie(
        SESSION_COOKIE, httponly=True, secure=settings.cookie_secure, samesite="strict"
    )
    return Message(message="Wylogowano.")


@router.post("/auth/verify-email")
async def verify_email(payload: TokenIn, session: SessionDep) -> Message:
    token = await tokens.consume(session, payload.token, tokens.VERIFY_EMAIL)
    if token is None:
        raise InvalidToken()
    user = await session.get(User, token.user_id)
    assert user is not None  # token znika kaskadowo z kontem
    if await accounts.email_taken(session, token.email, by_other_than=user):
        await session.rollback()
        raise Conflict("Ten adres e-mail potwierdziło już inne konto.")
    had_login = user.login is not None and user.email is None
    user.email = token.email
    user.email_verified_at = utcnow()
    await session.commit()
    if had_login:
        return Message(message="Adres potwierdzony. Od teraz logujesz się adresem e-mail.")
    return Message(message="Adres potwierdzony.")


@router.post("/auth/password-reset", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(
    payload: EmailIn,
    request: Request,
    background: BackgroundTasks,
    session: SessionDep,
    settings: SettingsDep,
    mail: MailDep,
) -> Message:
    _require_mail(mail)
    await rate_limit.check(
        session,
        (rate_limit.PASSWORD_RESET_PER_EMAIL, payload.email),
        (rate_limit.PASSWORD_RESET_PER_IP, _client_ip(request)),
    )
    # Tylko adres zapisany w koncie — nie adres z niepotwierdzonego linku konta sprzed #77
    # (literówka oddałaby konto właścicielowi tej skrzynki, design D6).
    user = await session.scalar(select(User).where(User.email == payload.email))
    if user is not None:
        token = await tokens.issue(
            session,
            user,
            tokens.RESET_PASSWORD,
            payload.email,
            timedelta(minutes=settings.password_reset_ttl_minutes),
        )
        await session.commit()
        message = emails.password_reset_message(settings, payload.email, token, display_name(user))
        _send_later(background, mail, message)
    # Ta sama odpowiedź bez względu na istnienie konta.
    return Message(
        message="Jeśli konto z tym adresem istnieje, wysłaliśmy na nie link do ustawienia "
        "nowego hasła. Sprawdź skrzynkę (także spam)."
    )


@router.post("/auth/password-reset/confirm")
async def confirm_password_reset(payload: PasswordResetConfirm, session: SessionDep) -> Message:
    token = await tokens.consume(session, payload.token, tokens.RESET_PASSWORD)
    if token is None:
        raise InvalidToken()
    user = await session.get(User, token.user_id)
    assert user is not None
    now = utcnow()
    user.password_hash = hash_password(payload.password)
    # Wszystkie dotychczasowe sesje konta (np. na zgubionym telefonie) przestają działać.
    user.sessions_valid_after = now
    # Link ze skrzynki dowodzi dostępu do adresu (design D6).
    if user.email == token.email and user.email_verified_at is None:
        user.email_verified_at = now
    await session.execute(
        delete(AuthToken).where(
            AuthToken.user_id == user.id,
            AuthToken.purpose == tokens.RESET_PASSWORD,
            AuthToken.used_at.is_(None),
        )
    )
    await session.commit()
    return Message(message="Hasło zostało zmienione. Zaloguj się nowym hasłem.")


async def _profile(session: SessionDep, user: User, mail: MailSender) -> Profile:
    household = await session.get(Household, user.household_id) if user.household_id else None
    verified = user.email_verified_at is not None
    email = user.email if verified else (await accounts.pending_email(session, user) or user.email)
    return Profile(
        id=user.id,
        login=user.login,
        name=user.name,
        email=email,
        email_verified=verified,
        email_status=accounts.email_status(user),
        verify_email_by=None if verified else user.verify_email_by,
        email_blocked=accounts.is_blocked(user, mail.delivers),
        mail_enabled=mail.delivers,
        household=HouseholdRef(id=household.id, name=household.name) if household else None,
    )


@router.get("/users/me")
async def me(user: CurrentUser, session: SessionDep, mail: MailDep) -> Profile:
    return await _profile(session, user, mail)


@router.patch("/users/me")
async def update_me(
    payload: ProfileUpdate, user: CurrentUser, session: SessionDep, mail: MailDep
) -> Profile:
    user.name = payload.name
    await session.commit()
    return await _profile(session, user, mail)


@router.post("/users/me/email")
async def set_email(
    payload: EmailIn,
    user: CurrentUser,
    background: BackgroundTasks,
    session: SessionDep,
    settings: SettingsDep,
    mail: MailDep,
) -> Profile:
    """Podanie adresu (konto sprzed #77), zmiana niepotwierdzonego adresu albo ponowne wysłanie
    linku (ten sam adres). Adres trafia do konta dopiero po kliknięciu linku."""
    if user.email_verified_at is not None:
        raise Conflict("Adres e-mail jest już potwierdzony.")
    _require_mail(mail)
    # Limit przed sprawdzeniem zajętości — inaczej endpoint służyłby do odpytywania o konta.
    await rate_limit.check(
        session,
        (rate_limit.VERIFICATION_PER_USER, str(user.id)),
        (rate_limit.VERIFICATION_PER_EMAIL, payload.email),
    )
    if await accounts.email_taken(session, payload.email, by_other_than=user):
        raise Conflict("Konto z tym adresem e-mail już istnieje.")
    await _start_verification(session, settings, mail, background, user, payload.email)
    return await _profile(session, user, mail)

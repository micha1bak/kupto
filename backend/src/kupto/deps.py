from typing import Annotated

from fastapi import Cookie, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from kupto.auth.accounts import email_status, is_blocked
from kupto.auth.security import SESSION_COOKIE, read_session, session_is_revoked
from kupto.config import Settings
from kupto.db import get_session
from kupto.errors import Conflict, Forbidden, Unauthorized
from kupto.mail import MailSender
from kupto.models import Household, User
from kupto.push.notifier import Notifier

NO_HOUSEHOLD = "no_household"
# Gospodarstwo zablokowane do podania (konto sprzed #77) albo potwierdzenia adresu (D3, D4).
EMAIL_REQUIRED = "email_required"
EMAIL_UNVERIFIED = "email_unverified"


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_notifier(request: Request) -> Notifier:
    return request.app.state.notifier


def get_mail_sender(request: Request) -> MailSender:
    return request.app.state.mail_sender


SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_app_settings)]
# Wysyłka powiadomień push — wołać po commicie zmiany (zob. `kupto.push.notifier`).
NotifierDep = Annotated[Notifier, Depends(get_notifier)]
# Wysyłka maili (#77); `mail.delivers` = czy wymagamy potwierdzenia adresów (design D8).
MailDep = Annotated[MailSender, Depends(get_mail_sender)]


async def get_current_user(
    session: SessionDep,
    settings: SettingsDep,
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> User:
    if token is None:
        raise Unauthorized("Wymagane zalogowanie.")
    claims = read_session(token, settings)
    user = await session.get(User, claims.user_id)
    # Reset hasła unieważnia sesje wydane wcześniej (#77, design D6).
    if user is None or session_is_revoked(claims, user.sessions_valid_after):
        raise Unauthorized("Sesja jest nieprawidłowa lub wygasła.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_household(user: CurrentUser, session: SessionDep, mail: MailDep) -> Household:
    # Konto bez potwierdzonego adresu po terminie (albo stare konto bez adresu) nie korzysta
    # z gospodarstwa, gdy wysyłka maili działa (#77, design D3, D4). Profil i adres — tak.
    if is_blocked(user, mail.delivers):
        if email_status(user) == "missing":
            raise Forbidden("Podaj adres e-mail, aby dalej korzystać z Kupto.", code=EMAIL_REQUIRED)
        raise Forbidden(
            "Potwierdź adres e-mail linkiem z wiadomości, aby dalej korzystać z Kupto.",
            code=EMAIL_UNVERIFIED,
        )
    # Przynależność sprawdzana w bazie przy każdym żądaniu, nie w tokenie (design: ryzyka JWT).
    if user.household_id is None:
        raise Conflict(
            "Najpierw utwórz gospodarstwo lub dołącz do istniejącego.", code=NO_HOUSEHOLD
        )
    household = await session.get(Household, user.household_id)
    assert household is not None
    return household


CurrentHousehold = Annotated[Household, Depends(get_current_household)]

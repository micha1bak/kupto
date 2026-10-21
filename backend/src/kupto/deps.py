from typing import Annotated

from fastapi import Cookie, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from kupto.auth.security import SESSION_COOKIE, read_session_token
from kupto.config import Settings
from kupto.db import get_session
from kupto.errors import Conflict, Unauthorized
from kupto.models import Household, User

NO_HOUSEHOLD = "no_household"


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_app_settings)]


async def get_current_user(
    session: SessionDep,
    settings: SettingsDep,
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> User:
    if token is None:
        raise Unauthorized("Wymagane zalogowanie.")
    user = await session.get(User, read_session_token(token, settings))
    if user is None:
        raise Unauthorized("Sesja jest nieprawidłowa lub wygasła.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_household(user: CurrentUser, session: SessionDep) -> Household:
    # Przynależność sprawdzana w bazie przy każdym żądaniu, nie w tokenie (design: ryzyka JWT).
    if user.household_id is None:
        raise Conflict(
            "Najpierw utwórz gospodarstwo lub dołącz do istniejącego.", code=NO_HOUSEHOLD
        )
    household = await session.get(Household, user.household_id)
    assert household is not None
    return household


CurrentHousehold = Annotated[Household, Depends(get_current_household)]

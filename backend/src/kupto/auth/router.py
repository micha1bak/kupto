from typing import Annotated

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from kupto.auth.security import (
    SESSION_COOKIE,
    create_session_token,
    hash_password,
    verify_password,
)
from kupto.deps import CurrentUser, SessionDep, SettingsDep
from kupto.errors import Conflict, Unauthorized
from kupto.models import Household, User

router = APIRouter(prefix="/api", tags=["auth"])


# Imię pokazywane domownikom w czacie i powiadomieniach (#78); spacje z brzegów są obcinane.
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]


class Credentials(BaseModel):
    login: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    name: Name


class ProfileUpdate(BaseModel):
    name: Name


class LoginCredentials(BaseModel):
    # Bez reguł długości: przy logowaniu każdy błąd danych ma dawać jednakowe 401.
    login: str = Field(max_length=200)
    password: str = Field(max_length=200)


class Message(BaseModel):
    message: str


class HouseholdRef(BaseModel):
    id: int
    name: str


class Profile(BaseModel):
    id: int
    login: str
    name: str | None  # None w koncie sprzed czatu grupowego — klient prosi o uzupełnienie
    household: HouseholdRef | None


@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
async def register(credentials: Credentials, session: SessionDep) -> Message:
    session.add(
        User(
            login=credentials.login,
            name=credentials.name,
            password_hash=hash_password(credentials.password),
        )
    )
    try:
        await session.commit()
    except IntegrityError as exc:
        raise Conflict("Ten login jest już zajęty.") from exc
    return Message(message="Konto zostało utworzone.")


@router.post("/auth/login")
async def login(
    credentials: LoginCredentials, response: Response, session: SessionDep, settings: SettingsDep
) -> Message:
    user = await session.scalar(select(User).where(User.login == credentials.login))
    if not verify_password(credentials.password, user.password_hash if user else None):
        raise Unauthorized("Nieprawidłowy login lub hasło.")
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


async def _profile(session: SessionDep, user: User) -> Profile:
    household = await session.get(Household, user.household_id) if user.household_id else None
    return Profile(
        id=user.id,
        login=user.login,
        name=user.name,
        household=HouseholdRef(id=household.id, name=household.name) if household else None,
    )


@router.get("/users/me")
async def me(user: CurrentUser, session: SessionDep) -> Profile:
    return await _profile(session, user)


@router.patch("/users/me")
async def update_me(payload: ProfileUpdate, user: CurrentUser, session: SessionDep) -> Profile:
    user.name = payload.name
    await session.commit()
    return await _profile(session, user)

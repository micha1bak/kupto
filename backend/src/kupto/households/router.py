from datetime import datetime

from fastapi import APIRouter, status
from pydantic import AliasChoices, BaseModel, Field

from kupto.deps import CurrentHousehold, CurrentUser, MailDep, SessionDep
from kupto.households import preferences, service
from kupto.households.preferences import PreferencesIn
from kupto.models import Household, display_name

router = APIRouter(prefix="/api/households", tags=["households"])


class HouseholdCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class MemberAdd(BaseModel):
    # Adres e-mail, a dla konta sprzed #77 bez adresu — login (stare klienty wysyłają `login`).
    email: str = Field(
        min_length=1, max_length=300, validation_alias=AliasChoices("email", "login")
    )


class MemberOut(BaseModel):
    id: int
    name: str  # imię (`display_name`) — bez loginu i adresu (#77)
    is_owner: bool
    joined_at: datetime | None


class HouseholdOut(BaseModel):
    id: int
    name: str
    members: list[MemberOut]


class PreferencesOut(PreferencesIn):
    updated_by: str | None
    updated_at: datetime | None


async def _household_out(session: SessionDep, household: Household) -> HouseholdOut:
    members = await service.list_members(session, household)
    return HouseholdOut(
        id=household.id,
        name=household.name,
        members=[
            MemberOut(
                id=m.id,
                name=display_name(m),
                is_owner=m.id == household.owner_id,
                joined_at=m.joined_household_at,
            )
            for m in members
        ],
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_household(
    payload: HouseholdCreate, user: CurrentUser, session: SessionDep
) -> HouseholdOut:
    household = await service.create_household(session, user, payload.name.strip())
    return await _household_out(session, household)


@router.get("/me")
async def get_my_household(household: CurrentHousehold, session: SessionDep) -> HouseholdOut:
    return await _household_out(session, household)


@router.post("/me/members", status_code=status.HTTP_201_CREATED)
async def add_member(
    payload: MemberAdd,
    user: CurrentUser,
    household: CurrentHousehold,
    session: SessionDep,
    mail: MailDep,
) -> HouseholdOut:
    # Gdy wysyłka działa, tylko potwierdzony adres — inaczej cudzy adres zarejestrowany bez
    # potwierdzenia mógłby trafić do gospodarstwa zamiast właściciela skrzynki (#77, D9).
    await service.add_member(session, user, household, payload.email, verified_only=mail.delivers)
    return await _household_out(session, household)


@router.delete("/me/members/{user_id}")
async def remove_member(
    user_id: int, user: CurrentUser, household: CurrentHousehold, session: SessionDep
) -> HouseholdOut:
    await service.remove_member(session, user, household, user_id)
    return await _household_out(session, household)


@router.post("/me/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave(user: CurrentUser, household: CurrentHousehold, session: SessionDep) -> None:
    await service.leave_household(session, user, household)


@router.get("/me/preferences")
async def get_preferences(household: CurrentHousehold, session: SessionDep) -> PreferencesOut:
    return _preferences_out(await preferences.load(session, household))


@router.put("/me/preferences")
async def put_preferences(
    payload: PreferencesIn, user: CurrentUser, household: CurrentHousehold, session: SessionDep
) -> PreferencesOut:
    """Zastępuje całe preferencje gospodarstwa — może każdy członek (design D2)."""
    return _preferences_out(await preferences.save(session, household, user, payload))


def _preferences_out(prefs: preferences.Preferences) -> PreferencesOut:
    return PreferencesOut(
        **preferences.to_input(prefs).model_dump(),
        updated_by=prefs.updated_by,
        updated_at=prefs.updated_at,
    )

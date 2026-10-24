from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from kupto.deps import CurrentHousehold, CurrentUser, SessionDep
from kupto.meal_plan import service
from kupto.meal_plan.schemas import PlanDayIn, PlanEntryOut, entry_out

router = APIRouter(prefix="/api/meal-plan", tags=["meal-plan"])


@router.get("")
async def list_entries(
    start: Annotated[date, Query(alias="from")],
    end: Annotated[date, Query(alias="to")],
    _: CurrentUser,
    household: CurrentHousehold,
    session: SessionDep,
) -> list[PlanEntryOut]:
    """Obiady z zakresu dat (włącznie, najwyżej 62 dni) rosnąco po dniu."""
    return [entry_out(e) for e in await service.list_entries(session, household, start, end)]


@router.put("/{day}")
async def set_day(
    day: date,
    payload: PlanDayIn,
    user: CurrentUser,
    household: CurrentHousehold,
    session: SessionDep,
) -> PlanEntryOut:
    """Ustawia danie na dzień — zastępuje poprzednie."""
    (entry,) = await service.save_days(session, household, user, {day: payload})
    return entry_out(entry)


@router.delete("/{day}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_day(
    day: date, _: CurrentUser, household: CurrentHousehold, session: SessionDep
) -> None:
    await service.delete_day(session, household, day)

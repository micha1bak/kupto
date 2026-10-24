"""Plan obiadów gospodarstwa (#44, design D1–D2): jeden obiad na dzień, wspólny dla członków.

Wspólny dla REST API (kalendarz, #47) i czatu. Przepis innego gospodarstwa jest
„nieznaleziony” (404), jak w bazie przepisów.
"""

from collections.abc import Mapping
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import ColumnElement, delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from kupto.db import utcnow
from kupto.errors import DomainError, NotFound
from kupto.lists.quantities import clean_name
from kupto.meal_plan.schemas import PlanDayIn
from kupto.models import Household, MealPlanEntry, Recipe, User

# Strefa gospodarstw — jak przypomnienia o zwykłych zakupach (`history.reminders`).
TIMEZONE = ZoneInfo("Europe/Warsaw")
MAX_RANGE_DAYS = 62
WEEKDAYS = ("poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela")


def today() -> date:
    return utcnow().astimezone(TIMEZONE).date()


def weekday(day: date) -> str:
    return WEEKDAYS[day.weekday()]


async def list_entries(
    session: AsyncSession, household: Household, start: date, end: date
) -> list[MealPlanEntry]:
    """Obiady z zakresu dat (włącznie) rosnąco po dniu; dni bez obiadu pominięte."""
    if start > end:
        raise DomainError("Początek zakresu jest po jego końcu.")
    if end - start >= timedelta(days=MAX_RANGE_DAYS):
        raise DomainError(f"Zakres planu może mieć najwyżej {MAX_RANGE_DAYS} dni.")
    return await _load(session, household, MealPlanEntry.day.between(start, end))


async def save_days(
    session: AsyncSession, household: Household, user: User, days: Mapping[date, PlanDayIn]
) -> list[MealPlanEntry]:
    """Ustawia danie na każdy z dni (zastępuje poprzednie); zwraca wpisy z przepisami.

    Najpierw sprawdza wszystkie przepisy, więc przy błędzie plan pozostaje bez zmian.
    """
    recipe_ids = {d.recipe_id for d in days.values() if d.recipe_id is not None}
    recipes = {
        r.id: r
        for r in await session.scalars(
            select(Recipe).where(Recipe.id.in_(recipe_ids), Recipe.household_id == household.id)
        )
    }
    if recipe_ids - set(recipes):
        raise NotFound("Nie ma takiego przepisu.")
    now = utcnow()
    for day, data in days.items():
        values = {
            "name": clean_name(data.name) if data.name else recipes[data.recipe_id].name,
            "recipe_id": data.recipe_id,
            "planned_by_id": user.id,
            "updated_at": now,
        }
        # Upsert: równoczesne ustawienie tego samego dnia nie kończy się błędem unikalności.
        await session.execute(
            insert(MealPlanEntry)
            .values(household_id=household.id, day=day, created_at=now, **values)
            .on_conflict_do_update(
                index_elements=[MealPlanEntry.household_id, MealPlanEntry.day], set_=values
            )
        )
    await session.commit()
    return await _load(session, household, MealPlanEntry.day.in_(list(days)), with_recipes=True)


async def delete_day(session: AsyncSession, household: Household, day: date) -> None:
    result = await session.execute(
        delete(MealPlanEntry).where(
            MealPlanEntry.household_id == household.id, MealPlanEntry.day == day
        )
    )
    if result.rowcount == 0:
        raise NotFound("Na ten dzień nie ma zaplanowanego obiadu.")
    await session.commit()


async def _load(
    session: AsyncSession,
    household: Household,
    condition: ColumnElement[bool],
    with_recipes: bool = False,
) -> list[MealPlanEntry]:
    options = [selectinload(MealPlanEntry.planned_by)]
    if with_recipes:
        options.append(selectinload(MealPlanEntry.recipe).selectinload(Recipe.ingredients))
    result = await session.scalars(
        select(MealPlanEntry)
        .where(MealPlanEntry.household_id == household.id, condition)
        .options(*options)
        .order_by(MealPlanEntry.day)
        .execution_options(populate_existing=True)
    )
    return list(result)

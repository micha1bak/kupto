from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from kupto.models import MealPlanEntry


class PlanDayIn(BaseModel):
    """Danie na dzień: własna nazwa, przepis gospodarstwa albo oba (nazwa domyślnie z przepisu)."""

    name: str | None = Field(default=None, max_length=100)
    recipe_id: int | None = None

    @field_validator("name", mode="before")
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value

    @model_validator(mode="after")
    def _name_or_recipe(self) -> "PlanDayIn":
        if self.name is None and self.recipe_id is None:
            raise ValueError("podaj nazwę dania albo przepis")
        return self


class PlanEntryOut(BaseModel):
    id: int
    day: date
    name: str
    recipe_id: int | None
    planned_by: str | None  # login; None także po usunięciu konta
    updated_at: datetime


def entry_out(entry: MealPlanEntry) -> PlanEntryOut:
    return PlanEntryOut(
        id=entry.id,
        day=entry.day,
        name=entry.name,
        recipe_id=entry.recipe_id,
        planned_by=entry.planned_by.login if entry.planned_by else None,
        updated_at=entry.updated_at,
    )

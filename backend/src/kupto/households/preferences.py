"""Preferencje żywieniowe gospodarstwa (#45, design D1–D3).

Wspólne dla członków gospodarstwa; brak wiersza w bazie = brak preferencji. Czat dostaje je
w instrukcjach (`for_model`), a plan obiadów (#44) może je odczytać tak samo: `load` + `for_model`.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from kupto.db import utcnow
from kupto.models import Household, HouseholdPreferences, User

MAX_ITEMS = 20
ITEM_MAX_LENGTH = 50
NOTES_MAX_LENGTH = 300
LIST_FIELDS = ("diets", "excluded", "disliked")


def _clean_items(value: Any) -> Any:
    """Przycina pozycje, pomija puste i powtórzone (bez wielkości liter), zachowuje kolejność."""
    if not isinstance(value, list):
        return value
    seen: set[str] = set()
    items = []
    for item in value:
        if not isinstance(item, str):
            return value  # walidacja typu zgłosi błąd
        item = " ".join(item.split())
        if item and item.casefold() not in seen:
            seen.add(item.casefold())
            items.append(item)
    return items


def _blank_to_none(value: Any) -> Any:
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


class PreferencesIn(BaseModel):
    people: int | None = Field(default=None, ge=1, le=20)
    diets: list[str] = Field(default_factory=list, max_length=MAX_ITEMS)
    excluded: list[str] = Field(default_factory=list, max_length=MAX_ITEMS)
    disliked: list[str] = Field(default_factory=list, max_length=MAX_ITEMS)
    max_cooking_minutes: int | None = Field(default=None, ge=5, le=480)
    notes: str | None = Field(default=None, max_length=NOTES_MAX_LENGTH)

    _clean_lists = field_validator(*LIST_FIELDS, mode="before")(_clean_items)
    _blank_notes = field_validator("notes", mode="before")(_blank_to_none)

    @field_validator(*LIST_FIELDS)
    @classmethod
    def _item_length(cls, items: list[str]) -> list[str]:
        for item in items:
            if len(item) > ITEM_MAX_LENGTH:
                raise ValueError(f"pozycja „{item[:20]}…” ma ponad {ITEM_MAX_LENGTH} znaków")
        return items


@dataclass(frozen=True)
class Preferences:
    people: int | None = None
    diets: list[str] = field(default_factory=list)
    excluded: list[str] = field(default_factory=list)
    disliked: list[str] = field(default_factory=list)
    max_cooking_minutes: int | None = None
    notes: str | None = None
    updated_by: str | None = None  # login; None także po usunięciu konta
    updated_at: datetime | None = None


async def load(session: AsyncSession, household: Household) -> Preferences:
    """Preferencje gospodarstwa; puste, gdy nikt ich jeszcze nie zapisał."""
    row = await session.scalar(
        select(HouseholdPreferences)
        .where(HouseholdPreferences.household_id == household.id)
        .options(selectinload(HouseholdPreferences.updated_by))
        .execution_options(populate_existing=True)
    )
    if row is None:
        return Preferences()
    return Preferences(
        people=row.people,
        diets=list(row.diets),
        excluded=list(row.excluded),
        disliked=list(row.disliked),
        max_cooking_minutes=row.max_cooking_minutes,
        notes=row.notes,
        updated_by=row.updated_by.login if row.updated_by else None,
        updated_at=row.updated_at,
    )


async def save(
    session: AsyncSession, household: Household, user: User, data: PreferencesIn
) -> Preferences:
    """Zastępuje całe preferencje gospodarstwa (upsert) i zapamiętuje, kto je zmienił."""
    values = {**data.model_dump(), "updated_by_id": user.id, "updated_at": utcnow()}
    await session.execute(
        insert(HouseholdPreferences)
        .values(household_id=household.id, **values)
        .on_conflict_do_update(index_elements=[HouseholdPreferences.household_id], set_=values)
    )
    await session.commit()
    return await load(session, household)


def to_input(prefs: Preferences) -> PreferencesIn:
    return PreferencesIn(
        people=prefs.people,
        diets=prefs.diets,
        excluded=prefs.excluded,
        disliked=prefs.disliked,
        max_cooking_minutes=prefs.max_cooking_minutes,
        notes=prefs.notes,
    )


def for_model(prefs: Preferences) -> dict[str, Any]:
    """Zwięzła postać dla modelu: tylko ustawione pola; pusty słownik = brak preferencji."""
    return {k: v for k, v in to_input(prefs).model_dump().items() if v not in (None, [])}

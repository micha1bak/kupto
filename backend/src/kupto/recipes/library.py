"""Baza przepisów gospodarstwa (#46) i dodawanie składników przepisu na listę.

Przepisy są wspólne dla gospodarstwa: każdy członek je czyta i zmienia, a przepis innego
gospodarstwa jest „nieznaleziony” (404), żeby nie zdradzać jego istnienia.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from kupto.db import utcnow
from kupto.errors import Conflict, NotFound
from kupto.lists import service as lists
from kupto.lists.quantities import clean_name, normalize_name
from kupto.lists.service import AddedNeed, NeedInput
from kupto.models import Household, Recipe, RecipeIngredient, User
from kupto.recipes.schemas import IngredientIn, RecipeIn

RECIPE_EXISTS = "recipe_exists"
NOTE_MAX_LENGTH = 200


@dataclass(frozen=True)
class RecipeSummary:
    recipe: Recipe
    ingredient_count: int


async def list_recipes(session: AsyncSession, household: Household) -> list[RecipeSummary]:
    """Przepisy gospodarstwa alfabetycznie (bez wielkości liter) z liczbą składników."""
    count = func.count(RecipeIngredient.id)
    rows = await session.execute(
        select(Recipe, count)
        .outerjoin(RecipeIngredient, RecipeIngredient.recipe_id == Recipe.id)
        .where(Recipe.household_id == household.id)
        .group_by(Recipe.id)
        .order_by(Recipe.normalized_name)
    )
    return [RecipeSummary(recipe, n) for recipe, n in rows]


async def get_recipe(session: AsyncSession, household: Household, recipe_id: int) -> Recipe:
    recipe = await session.scalar(
        select(Recipe)
        .where(Recipe.id == recipe_id, Recipe.household_id == household.id)
        .options(selectinload(Recipe.ingredients), selectinload(Recipe.created_by))
        .execution_options(populate_existing=True)
    )
    if recipe is None:
        raise NotFound("Nie ma takiego przepisu.")
    return recipe


async def create_recipe(
    session: AsyncSession, household: Household, user: User, data: RecipeIn
) -> Recipe:
    await _ensure_name_free(session, household, data.name)
    recipe = Recipe(household_id=household.id, created_by_id=user.id, created_by=user)
    _apply(recipe, data)
    session.add(recipe)
    await _commit(session, data.name)
    return recipe


async def update_recipe(
    session: AsyncSession, household: Household, recipe_id: int, data: RecipeIn
) -> Recipe:
    """Zastępuje pola i całą listę składników; identyfikator przepisu zostaje ten sam."""
    recipe = await get_recipe(session, household, recipe_id)
    await _ensure_name_free(session, household, data.name, except_id=recipe.id)
    _apply(recipe, data)
    recipe.updated_at = utcnow()
    await _commit(session, data.name)
    return recipe


async def delete_recipe(session: AsyncSession, household: Household, recipe_id: int) -> None:
    recipe = await get_recipe(session, household, recipe_id)
    await session.delete(recipe)
    await session.commit()


def ingredient_note(dish: str, note: str | None) -> str:
    """Notatka zapotrzebowania ze składnika: „na: <danie>” albo „na: <danie> (<notatka>)”."""
    text = f"na: {dish} ({note})" if note else f"na: {dish}"
    return text if len(text) <= NOTE_MAX_LENGTH else text[: NOTE_MAX_LENGTH - 1] + "…"


async def add_to_list(
    session: AsyncSession,
    household: Household,
    user: User,
    recipe_id: int,
    ingredient_ids: Sequence[int],
) -> list[AddedNeed]:
    """Dodaje wybrane składniki przepisu jako zapotrzebowania autora (kolejność z przepisu).

    Używa wspólnego `lists.service.add_needs` — produkt już na liście jest scalany.
    """
    recipe = await get_recipe(session, household, recipe_id)
    wanted = set(ingredient_ids)
    if not wanted <= {i.id for i in recipe.ingredients}:
        raise NotFound("Składnik nie należy do tego przepisu.")
    inputs = [
        NeedInput(
            name=i.name,
            amount=i.amount,
            unit=i.unit,
            note=ingredient_note(recipe.name, i.note),
            category=i.category,
        )
        for i in recipe.ingredients
        if i.id in wanted
    ]
    return await lists.add_needs(session, household, user, inputs)


def _apply(recipe: Recipe, data: RecipeIn) -> None:
    recipe.name = clean_name(data.name)
    recipe.normalized_name = normalize_name(data.name)
    recipe.servings = data.servings
    recipe.source_url = data.source_url
    recipe.instructions = data.instructions
    recipe.ingredients = [_ingredient(position, i) for position, i in enumerate(data.ingredients)]


def _ingredient(position: int, data: IngredientIn) -> RecipeIngredient:
    return RecipeIngredient(
        position=position,
        name=clean_name(data.name),
        amount=data.amount,
        unit=data.unit,
        note=data.note,
        category=data.category,
    )


async def _ensure_name_free(
    session: AsyncSession, household: Household, name: str, except_id: int | None = None
) -> None:
    statement = select(Recipe.id).where(
        Recipe.household_id == household.id, Recipe.normalized_name == normalize_name(name)
    )
    if except_id is not None:
        statement = statement.where(Recipe.id != except_id)
    if await session.scalar(statement) is not None:
        raise _name_taken(name)


async def _commit(session: AsyncSession, name: str) -> None:
    try:
        await session.commit()
    except IntegrityError as exc:
        # Równoczesny zapis przepisu o tej samej nazwie (unikalność w bazie).
        await session.rollback()
        raise _name_taken(name) from exc


def _name_taken(name: str) -> Conflict:
    return Conflict(
        f"Przepis „{clean_name(name)}” jest już zapisany — wybierz inną nazwę.", code=RECIPE_EXISTS
    )

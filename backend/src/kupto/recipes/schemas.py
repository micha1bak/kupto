from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from kupto.models import Category, Recipe, RecipeIngredient, Unit

# Tyle składników zwraca też ekstrakcja przepisu ze strony (`kupto.recipes.extract`).
MAX_INGREDIENTS = 60
# Tyle mieści wiadomość czatu, z której przepis zwykle pochodzi.
MAX_INSTRUCTIONS = 8000


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


class IngredientIn(BaseModel):
    name: str = Field(min_length=1, max_length=100, pattern=r"\S")
    amount: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=3)
    unit: Unit | None = None
    # Miara kuchenna bez jednostki listy („2 szklanki”) albo cecha produktu („pszenna”).
    note: str | None = Field(default=None, max_length=200)
    category: Category | None = None

    _blank_note = field_validator("note", mode="before")(_blank_to_none)


class RecipeIn(BaseModel):
    name: str = Field(min_length=1, max_length=100, pattern=r"\S")
    servings: str | None = Field(default=None, max_length=50)
    source_url: str | None = Field(default=None, max_length=2000, pattern=r"^https?://\S+$")
    instructions: str | None = Field(default=None, max_length=MAX_INSTRUCTIONS)
    ingredients: list[IngredientIn] = Field(min_length=1, max_length=MAX_INGREDIENTS)

    _blank_optional = field_validator("servings", "source_url", "instructions", mode="before")(
        _blank_to_none
    )


class ToListIn(BaseModel):
    ingredient_ids: list[int] = Field(min_length=1, max_length=MAX_INGREDIENTS)


class IngredientOut(BaseModel):
    id: int
    name: str
    amount: float | None
    unit: Unit | None
    note: str | None
    category: Category | None


class RecipeSummaryOut(BaseModel):
    id: int
    name: str
    servings: str | None
    ingredient_count: int
    updated_at: datetime


class RecipeOut(BaseModel):
    id: int
    name: str
    servings: str | None
    source_url: str | None
    instructions: str | None
    # W kolejności z przepisu.
    ingredients: list[IngredientOut]
    created_by: str | None
    created_at: datetime
    updated_at: datetime


class AddedOut(BaseModel):
    name: str
    category: Category
    already_on_list: bool


class ToListOut(BaseModel):
    added: list[AddedOut]


def ingredient_out(ingredient: RecipeIngredient) -> IngredientOut:
    return IngredientOut(
        id=ingredient.id,
        name=ingredient.name,
        amount=float(ingredient.amount) if ingredient.amount is not None else None,
        unit=ingredient.unit,
        note=ingredient.note,
        category=ingredient.category,
    )


def recipe_out(recipe: Recipe) -> RecipeOut:
    return RecipeOut(
        id=recipe.id,
        name=recipe.name,
        servings=recipe.servings,
        source_url=recipe.source_url,
        instructions=recipe.instructions,
        ingredients=[ingredient_out(i) for i in recipe.ingredients],
        created_by=recipe.created_by.login if recipe.created_by else None,
        created_at=recipe.created_at,
        updated_at=recipe.updated_at,
    )

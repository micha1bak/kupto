from fastapi import APIRouter, status

from kupto.deps import CurrentHousehold, CurrentUser, NotifierDep, SessionDep
from kupto.lists import notifications
from kupto.recipes import library
from kupto.recipes.schemas import (
    AddedOut,
    RecipeIn,
    RecipeOut,
    RecipeSummaryOut,
    ToListIn,
    ToListOut,
    recipe_out,
)

router = APIRouter(prefix="/api/recipes", tags=["recipes"])


@router.get("")
async def list_recipes(
    _: CurrentUser, household: CurrentHousehold, session: SessionDep
) -> list[RecipeSummaryOut]:
    """Przepisy gospodarstwa alfabetycznie."""
    return [
        RecipeSummaryOut(
            id=s.recipe.id,
            name=s.recipe.name,
            servings=s.recipe.servings,
            ingredient_count=s.ingredient_count,
            updated_at=s.recipe.updated_at,
        )
        for s in await library.list_recipes(session, household)
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_recipe(
    payload: RecipeIn, user: CurrentUser, household: CurrentHousehold, session: SessionDep
) -> RecipeOut:
    return recipe_out(await library.create_recipe(session, household, user, payload))


@router.get("/{recipe_id}")
async def get_recipe(
    recipe_id: int, _: CurrentUser, household: CurrentHousehold, session: SessionDep
) -> RecipeOut:
    return recipe_out(await library.get_recipe(session, household, recipe_id))


@router.put("/{recipe_id}")
async def update_recipe(
    recipe_id: int,
    payload: RecipeIn,
    _: CurrentUser,
    household: CurrentHousehold,
    session: SessionDep,
) -> RecipeOut:
    """Zastępuje cały przepis (pola i listę składników)."""
    return recipe_out(await library.update_recipe(session, household, recipe_id, payload))


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recipe(
    recipe_id: int, _: CurrentUser, household: CurrentHousehold, session: SessionDep
) -> None:
    await library.delete_recipe(session, household, recipe_id)


@router.post("/{recipe_id}/to-list")
async def add_to_list(
    recipe_id: int,
    payload: ToListIn,
    user: CurrentUser,
    household: CurrentHousehold,
    session: SessionDep,
    notifier: NotifierDep,
) -> ToListOut:
    """Dodaje wybrane składniki jako zapotrzebowania autora z notatką „na: <przepis>”."""
    added = await library.add_to_list(session, household, user, recipe_id, payload.ingredient_ids)
    await notifications.items_added(session, notifier, household, user)
    return ToListOut(
        added=[
            AddedOut(name=a.item_name, category=a.category, already_on_list=a.merged) for a in added
        ]
    )

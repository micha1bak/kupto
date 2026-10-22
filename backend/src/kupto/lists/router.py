from fastapi import APIRouter, status

from kupto.deps import CurrentHousehold, CurrentUser, SessionDep
from kupto.lists import category_order, service, shopping_status
from kupto.lists.schemas import (
    CategoryMove,
    CategoryOrderEntry,
    ListOut,
    NeedCreate,
    NeedUpdate,
    category_order_out,
    list_out,
)
from kupto.lists.service import NeedInput
from kupto.models import Category, Household, User

router = APIRouter(prefix="/api/list", tags=["list"])


async def _current_list(session: SessionDep, household: Household, user: User) -> ListOut:
    """Wspólna lista gospodarstwa w kolejności kategorii danego użytkownika."""
    shopping_list = await service.get_list(session, household)
    return list_out(
        shopping_list,
        await category_order.get_order(session, user),
        await shopping_status.active_shoppers(session, household),
    )


@router.get("")
async def get_list(user: CurrentUser, household: CurrentHousehold, session: SessionDep) -> ListOut:
    return await _current_list(session, household, user)


@router.post("/needs", status_code=status.HTTP_201_CREATED)
async def add_need(
    payload: NeedCreate, user: CurrentUser, household: CurrentHousehold, session: SessionDep
) -> ListOut:
    await service.add_needs(session, household, user, [NeedInput(**payload.model_dump())])
    return await _current_list(session, household, user)


@router.patch("/needs/{need_id}")
async def update_need(
    need_id: int,
    payload: NeedUpdate,
    user: CurrentUser,
    household: CurrentHousehold,
    session: SessionDep,
) -> ListOut:
    changes = payload.model_dump(include=payload.model_fields_set)
    await service.update_need(session, household, user, need_id, changes)
    return await _current_list(session, household, user)


@router.delete("/needs/{need_id}")
async def withdraw_need(
    need_id: int, user: CurrentUser, household: CurrentHousehold, session: SessionDep
) -> ListOut:
    await service.withdraw_need(session, household, user, need_id)
    return await _current_list(session, household, user)


@router.delete("/items/{item_id}")
async def remove_item(
    item_id: int, user: CurrentUser, household: CurrentHousehold, session: SessionDep
) -> ListOut:
    await service.remove_item(session, household, item_id)
    return await _current_list(session, household, user)


@router.post("/items/{item_id}/bought")
async def mark_bought(
    item_id: int, user: CurrentUser, household: CurrentHousehold, session: SessionDep
) -> ListOut:
    await service.set_bought(session, household, user, [item_id], bought=True)
    return await _current_list(session, household, user)


@router.delete("/items/{item_id}/bought")
async def unmark_bought(
    item_id: int, user: CurrentUser, household: CurrentHousehold, session: SessionDep
) -> ListOut:
    await service.set_bought(session, household, user, [item_id], bought=False)
    return await _current_list(session, household, user)


@router.post("/finish")
async def finish_shopping(
    user: CurrentUser, household: CurrentHousehold, session: SessionDep
) -> ListOut:
    await service.finish_shopping(session, household, user)
    return await _current_list(session, household, user)


# Status „robię zakupy” zalogowanego użytkownika; widać go w `shoppers` każdej odpowiedzi listy.


@router.post("/shopping")
async def start_shopping(
    user: CurrentUser, household: CurrentHousehold, session: SessionDep
) -> ListOut:
    await shopping_status.start(session, user)
    return await _current_list(session, household, user)


@router.delete("/shopping")
async def stop_shopping(
    user: CurrentUser, household: CurrentHousehold, session: SessionDep
) -> ListOut:
    await shopping_status.stop(session, user)
    return await _current_list(session, household, user)


# Kolejność kategorii jest per użytkownik; gospodarstwo jest wymagane jak w całym /api/list.


@router.get("/category-order")
async def get_category_order(
    user: CurrentUser, _: CurrentHousehold, session: SessionDep
) -> list[CategoryOrderEntry]:
    return category_order_out(await category_order.get_order(session, user))


@router.put("/category-order/{category}")
async def pin_category(
    category: Category,
    payload: CategoryMove,
    user: CurrentUser,
    household: CurrentHousehold,
    session: SessionDep,
) -> ListOut:
    await category_order.pin(session, user, category, payload.after, payload.before)
    return await _current_list(session, household, user)


@router.delete("/category-order/{category}")
async def unpin_category(
    category: Category, user: CurrentUser, household: CurrentHousehold, session: SessionDep
) -> ListOut:
    await category_order.unpin(session, user, category)
    return await _current_list(session, household, user)


@router.delete("/category-order")
async def reset_category_order(
    user: CurrentUser, household: CurrentHousehold, session: SessionDep
) -> ListOut:
    await category_order.reset(session, user)
    return await _current_list(session, household, user)

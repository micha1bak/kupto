from fastapi import APIRouter, status

from kupto.deps import CurrentHousehold, CurrentUser, SessionDep
from kupto.lists import service
from kupto.lists.schemas import ListOut, NeedCreate, NeedUpdate, list_out
from kupto.lists.service import NeedInput
from kupto.models import Household

router = APIRouter(prefix="/api/list", tags=["list"])


async def _current_list(session: SessionDep, household: Household) -> ListOut:
    return list_out(await service.get_list(session, household))


@router.get("")
async def get_list(household: CurrentHousehold, session: SessionDep) -> ListOut:
    return await _current_list(session, household)


@router.post("/needs", status_code=status.HTTP_201_CREATED)
async def add_need(
    payload: NeedCreate, user: CurrentUser, household: CurrentHousehold, session: SessionDep
) -> ListOut:
    await service.add_needs(session, household, user, [NeedInput(**payload.model_dump())])
    return await _current_list(session, household)


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
    return await _current_list(session, household)


@router.delete("/needs/{need_id}")
async def withdraw_need(
    need_id: int, user: CurrentUser, household: CurrentHousehold, session: SessionDep
) -> ListOut:
    await service.withdraw_need(session, household, user, need_id)
    return await _current_list(session, household)


@router.delete("/items/{item_id}")
async def remove_item(item_id: int, household: CurrentHousehold, session: SessionDep) -> ListOut:
    await service.remove_item(session, household, item_id)
    return await _current_list(session, household)


@router.post("/items/{item_id}/bought")
async def mark_bought(
    item_id: int, user: CurrentUser, household: CurrentHousehold, session: SessionDep
) -> ListOut:
    await service.set_bought(session, household, user, [item_id], bought=True)
    return await _current_list(session, household)


@router.delete("/items/{item_id}/bought")
async def unmark_bought(
    item_id: int, user: CurrentUser, household: CurrentHousehold, session: SessionDep
) -> ListOut:
    await service.set_bought(session, household, user, [item_id], bought=False)
    return await _current_list(session, household)


@router.post("/finish")
async def finish_shopping(household: CurrentHousehold, session: SessionDep) -> ListOut:
    await service.finish_shopping(session, household)
    return await _current_list(session, household)

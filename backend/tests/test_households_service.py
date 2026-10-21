import pytest
from sqlalchemy import func, select

from kupto.errors import Conflict, Forbidden, NotFound
from kupto.households import service
from kupto.models import ChatMessage, Household, ShoppingList, User


async def make_user(session, login: str) -> User:
    user = User(login=login, password_hash="x")
    session.add(user)
    await session.commit()
    return user


async def test_create_household_makes_owner_and_empty_list(session):
    ala = await make_user(session, "ala")

    household = await service.create_household(session, ala, "Dom")

    assert household.owner_id == ala.id
    assert ala.household_id == household.id
    shopping_list = await session.scalar(
        select(ShoppingList).where(ShoppingList.household_id == household.id)
    )
    assert shopping_list is not None


async def test_cannot_create_second_household(session):
    ala = await make_user(session, "ala")
    await service.create_household(session, ala, "Dom")

    with pytest.raises(Conflict):
        await service.create_household(session, ala, "Działka")


async def test_only_owner_adds_members(session):
    ala, ola, ewa = [await make_user(session, n) for n in ("ala", "ola", "ewa")]
    household = await service.create_household(session, ala, "Dom")
    await service.add_member(session, ala, household, "ola")

    with pytest.raises(Forbidden):
        await service.add_member(session, ola, household, "ewa")
    assert ewa.household_id is None


async def test_add_member_errors(session):
    ala, ola = await make_user(session, "ala"), await make_user(session, "ola")
    household = await service.create_household(session, ala, "Dom")
    await service.create_household(session, ola, "Inny dom")

    with pytest.raises(NotFound):
        await service.add_member(session, ala, household, "nieznany")
    with pytest.raises(Conflict):
        await service.add_member(session, ala, household, "ola")


async def test_owner_cannot_remove_self(session):
    ala = await make_user(session, "ala")
    household = await service.create_household(session, ala, "Dom")

    with pytest.raises(Forbidden):
        await service.remove_member(session, ala, household, ala.id)


async def test_remove_member_deletes_their_chat_history_in_household(session):
    ala, ola = await make_user(session, "ala"), await make_user(session, "ola")
    household = await service.create_household(session, ala, "Dom")
    await service.add_member(session, ala, household, "ola")
    session.add(ChatMessage(user_id=ola.id, household_id=household.id, role="user", content="hej"))
    await session.commit()

    await service.remove_member(session, ala, household, ola.id)

    assert ola.household_id is None
    assert await session.scalar(select(func.count(ChatMessage.id))) == 0


async def test_owner_leaving_transfers_ownership_to_longest_member(session):
    ala, ola, ewa = [await make_user(session, n) for n in ("ala", "ola", "ewa")]
    household = await service.create_household(session, ala, "Dom")
    await service.add_member(session, ala, household, "ola")
    await service.add_member(session, ala, household, "ewa")

    await service.leave_household(session, ala, household)

    assert household.owner_id == ola.id
    assert [m.login for m in await service.list_members(session, household)] == ["ola", "ewa"]


async def test_last_member_leaving_deletes_household(session):
    ala = await make_user(session, "ala")
    household = await service.create_household(session, ala, "Dom")
    session.add(ChatMessage(user_id=ala.id, household_id=household.id, role="user", content="hej"))
    await session.commit()

    await service.leave_household(session, ala, household)

    assert await session.scalar(select(func.count(Household.id))) == 0
    assert await session.scalar(select(func.count(ShoppingList.id))) == 0
    assert await session.scalar(select(func.count(ChatMessage.id))) == 0

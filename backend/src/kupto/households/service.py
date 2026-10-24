from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from kupto.auth import accounts
from kupto.db import utcnow
from kupto.errors import Conflict, Forbidden, NotFound
from kupto.lists import events, shopping_status
from kupto.models import ChatMessage, ChatPendingAction, Household, ShoppingList, User


async def create_household(session: AsyncSession, user: User, name: str) -> Household:
    if user.household_id is not None:
        raise Conflict("Należysz już do gospodarstwa.")
    household = Household(name=name, owner_id=user.id, shopping_list=ShoppingList())
    session.add(household)
    await session.flush()
    _join(user, household)
    await session.commit()
    return household


async def list_members(session: AsyncSession, household: Household) -> list[User]:
    result = await session.scalars(
        select(User)
        .where(User.household_id == household.id)
        .order_by(User.joined_household_at, User.id)
    )
    return list(result)


async def add_member(
    session: AsyncSession,
    actor: User,
    household: Household,
    identifier: str,
    *,
    verified_only: bool = False,
) -> User:
    """Dodaje konto po adresie e-mail albo (konto bez adresu) po loginie."""
    _require_owner(actor, household)
    user = await accounts.find_by_identifier(session, identifier, verified_only=verified_only)
    if user is None:
        raise NotFound(
            "Nie znaleziono konta o tym adresie e-mail"
            + (" (adres musi być potwierdzony)." if verified_only else ".")
        )
    if user.household_id is not None:
        raise Conflict("Ten użytkownik należy już do gospodarstwa.")
    _join(user, household)
    await session.commit()
    return user


async def remove_member(
    session: AsyncSession, actor: User, household: Household, user_id: int
) -> None:
    _require_owner(actor, household)
    if user_id == household.owner_id:
        raise Forbidden("Właściciel nie może usunąć siebie — użyj opuszczenia gospodarstwa.")
    user = await session.get(User, user_id)
    if user is None or user.household_id != household.id:
        raise NotFound("Ten użytkownik nie jest członkiem gospodarstwa.")
    await _detach(session, user, household)
    await session.commit()


async def leave_household(session: AsyncSession, user: User, household: Household) -> None:
    others = [m for m in await list_members(session, household) if m.id != user.id]
    await _detach(session, user, household)
    if not others:
        # Ostatni członek: gospodarstwo, lista i historia czatu znikają kaskadowo.
        await session.delete(household)
    elif household.owner_id == user.id:
        household.owner_id = others[0].id
    await session.commit()


def _join(user: User, household: Household) -> None:
    user.household_id = household.id
    user.joined_household_at = utcnow()


async def _detach(session: AsyncSession, user: User, household: Household) -> None:
    # Prywatna historia czatu dotyczy listy tego gospodarstwa, więc nie przechodzi dalej.
    await session.execute(
        delete(ChatMessage).where(
            ChatMessage.user_id == user.id, ChatMessage.household_id == household.id
        )
    )
    await session.execute(delete(ChatPendingAction).where(ChatPendingAction.user_id == user.id))
    # Status zakupów dotyczy tego gospodarstwa — nie może pojawić się w następnym.
    if await shopping_status.clear(session, user):
        # Pozostali członkowie widzą na liście, kto robi zakupy — ten wskaźnik właśnie znika.
        await events.list_changed(session, household.id)
    user.household_id = None
    user.joined_household_at = None
    await session.flush()
    # Otwarte strumienie zmian listy tego użytkownika mają się zakończyć (po commicie).
    await events.member_left(session, household.id, user.id)


def _require_owner(actor: User, household: Household) -> None:
    if household.owner_id != actor.id:
        raise Forbidden("Tylko właściciel może zarządzać członkami gospodarstwa.")

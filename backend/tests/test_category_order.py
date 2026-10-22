import pytest

from kupto.errors import DomainError
from kupto.lists import category_order
from kupto.models import Category, User

AUTOMATIC = list(Category)


@pytest.fixture
async def ala(session):
    user = User(login="ala", password_hash="x")
    session.add(user)
    await session.commit()
    return user


def moved(category, index):
    order = [c for c in AUTOMATIC if c != category]
    order.insert(index, category)
    return order


async def test_without_pins_order_is_automatic(session, ala):
    order = await category_order.get_order(session, ala)

    assert (order.categories, order.pinned) == (AUTOMATIC, frozenset())


async def test_pin_at_start_end_and_after_neighbour(session, ala):
    await category_order.pin(session, ala, Category.HOUSEHOLD, after=None, before=Category.BREAD)
    assert (await category_order.get_order(session, ala)).categories == moved(Category.HOUSEHOLD, 0)

    await category_order.reset(session, ala)
    await category_order.pin(
        session, ala, Category.VEGETABLES_FRUITS, after=Category.DRINKS, before=None
    )
    order = await category_order.get_order(session, ala)
    assert order.categories == moved(Category.VEGETABLES_FRUITS, 9)

    await category_order.reset(session, ala)
    await category_order.pin(
        session, ala, Category.HOUSEHOLD, after=Category.BREAD, before=Category.DAIRY
    )
    order = await category_order.get_order(session, ala)
    assert order.categories == moved(Category.HOUSEHOLD, 2)
    assert order.pinned == {Category.HOUSEHOLD}


async def test_next_pin_keeps_relative_place_of_earlier_pins(session, ala):
    await category_order.pin(session, ala, Category.HOUSEHOLD, after=None, before=Category.DAIRY)
    await category_order.pin(session, ala, Category.DRINKS, after=None, before=Category.HOUSEHOLD)

    order = await category_order.get_order(session, ala)
    assert order.categories[:3] == [Category.DRINKS, Category.HOUSEHOLD, Category.VEGETABLES_FRUITS]
    assert order.pinned == {Category.DRINKS, Category.HOUSEHOLD}


async def test_moving_a_pinned_category_again(session, ala):
    await category_order.pin(session, ala, Category.HOUSEHOLD, after=None, before=Category.DAIRY)
    await category_order.pin(session, ala, Category.HOUSEHOLD, after=Category.DAIRY, before=None)

    order = await category_order.get_order(session, ala)
    assert order.categories == moved(Category.HOUSEHOLD, 9)
    assert order.pinned == {Category.HOUSEHOLD}


async def test_unpin_returns_category_to_automatic_place(session, ala):
    await category_order.pin(session, ala, Category.HOUSEHOLD, after=None, before=Category.DAIRY)
    await category_order.pin(session, ala, Category.OTHER, after=None, before=Category.HOUSEHOLD)

    await category_order.unpin(session, ala, Category.HOUSEHOLD)

    order = await category_order.get_order(session, ala)
    assert order.categories == moved(Category.OTHER, 0)
    assert order.pinned == {Category.OTHER}


async def test_pin_relative_to_itself_is_rejected(session, ala):
    with pytest.raises(DomainError):
        await category_order.pin(session, ala, Category.DAIRY, after=Category.DAIRY, before=None)

    assert (await category_order.get_order(session, ala)).pinned == frozenset()

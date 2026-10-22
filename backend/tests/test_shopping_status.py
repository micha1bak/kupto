from datetime import timedelta

import pytest

from kupto.db import utcnow
from kupto.households import service as households
from kupto.lists import service, shopping_status
from kupto.lists.service import NeedInput
from kupto.lists.shopping_status import SHOPPING_STATUS_TTL
from kupto.models import User


@pytest.fixture
async def home(session):
    """Gospodarstwo „Dom” z członkami ala (właściciel) i ola oraz osobne gospodarstwo ewy."""
    ala, ola, ewa = (User(login=n, password_hash="x") for n in ("ala", "ola", "ewa"))
    session.add_all([ala, ola, ewa])
    await session.commit()
    household = await households.create_household(session, ala, "Dom")
    await households.add_member(session, ala, household, "ola")
    other = await households.create_household(session, ewa, "Inny dom")
    return household, ala, ola, other, ewa


async def shoppers(session, household, now=None):
    return [
        (s.login, s.since) for s in await shopping_status.active_shoppers(session, household, now)
    ]


async def test_start_sets_status_visible_to_household(session, home):
    household, ala, _, other, _ = home
    now = utcnow()

    assert await shopping_status.start(session, ala, now) is True

    (shopper,) = await shopping_status.active_shoppers(session, household, now)
    assert (shopper.user_id, shopper.login, shopper.since) == (ala.id, "ala", now)
    assert shopper.expires_at == now + timedelta(hours=3)
    assert await shoppers(session, other, now) == []


async def test_repeated_start_keeps_original_since(session, home):
    household, ala, *_ = home
    began = utcnow()
    await shopping_status.start(session, ala, began)

    assert await shopping_status.start(session, ala, began + timedelta(minutes=30)) is False

    assert await shoppers(session, household) == [("ala", began)]


async def test_status_expires_after_three_hours(session, home):
    household, ala, *_ = home
    began = utcnow() - SHOPPING_STATUS_TTL - timedelta(minutes=1)
    await shopping_status.start(session, ala, began)

    assert await shoppers(session, household) == []
    assert await shoppers(session, household, began + SHOPPING_STATUS_TTL - timedelta(seconds=1))


async def test_start_after_expiry_begins_new_status(session, home):
    household, ala, *_ = home
    await shopping_status.start(session, ala, utcnow() - timedelta(hours=4))
    now = utcnow()

    assert await shopping_status.start(session, ala, now) is True

    assert await shoppers(session, household) == [("ala", now)]


async def test_stop_reports_whether_status_was_active(session, home):
    household, ala, ola, *_ = home
    await shopping_status.start(session, ala)
    await shopping_status.start(session, ola)

    assert await shopping_status.stop(session, ala) is True
    assert await shopping_status.stop(session, ala) is False

    assert [login for login, _ in await shoppers(session, household)] == ["ola"]


async def test_stop_of_expired_status_reports_inactive(session, home):
    _, ala, *_ = home
    await shopping_status.start(session, ala, utcnow() - timedelta(hours=4))

    assert await shopping_status.stop(session, ala) is False
    assert ala.shopping_since is None


async def test_shoppers_are_ordered_by_start(session, home):
    household, ala, ola, *_ = home
    now = utcnow()
    await shopping_status.start(session, ola, now - timedelta(minutes=10))
    await shopping_status.start(session, ala, now)

    assert await shoppers(session, household) == [
        ("ola", now - timedelta(minutes=10)),
        ("ala", now),
    ]


async def test_finish_shopping_clears_only_finishers_status(session, home):
    household, ala, ola, *_ = home
    await service.add_needs(session, household, ala, [NeedInput("mleko")])
    item = (await service.get_list(session, household)).items[0]
    await service.set_bought(session, household, ala, [item.id], bought=True)
    await shopping_status.start(session, ala)
    await shopping_status.start(session, ola)

    await service.finish_shopping(session, household, ala)

    assert [login for login, _ in await shoppers(session, household)] == ["ola"]


async def test_finish_shopping_without_bought_items_clears_status(session, home):
    household, ala, *_ = home
    await shopping_status.start(session, ala)

    assert await service.finish_shopping(session, household, ala) == 0

    assert await shoppers(session, household) == []


async def test_leaving_household_clears_status(session, home):
    household, ala, ola, *_ = home
    await shopping_status.start(session, ola)

    await households.leave_household(session, ola, household)

    assert ola.shopping_since is None
    other = await households.create_household(session, ola, "Nowy dom")
    assert await shoppers(session, other) == []


async def test_removing_member_clears_status(session, home):
    household, ala, ola, *_ = home
    await shopping_status.start(session, ola)

    await households.remove_member(session, ala, household, ola.id)

    await session.refresh(ola)
    assert ola.shopping_since is None

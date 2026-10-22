from decimal import Decimal

import pytest

from kupto.errors import Forbidden, NotFound
from kupto.households import service as households
from kupto.lists import service
from kupto.lists.quantities import aggregate_quantities
from kupto.lists.service import NeedInput
from kupto.models import Category, Unit, User


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


async def items_by_name(session, household):
    return {item.name: item for item in (await service.get_list(session, household)).items}


async def test_need_keeps_requester_amount_unit_and_note(session, home):
    household, ala, *_ = home

    await service.add_needs(
        session,
        household,
        ala,
        [NeedInput("mleko", Decimal(2), Unit.L, "bez laktozy", Category.DAIRY)],
    )

    item = (await items_by_name(session, household))["mleko"]
    (need,) = item.needs
    assert (need.user.login, need.amount, need.unit, need.note) == (
        "ala",
        Decimal(2),
        Unit.L,
        "bez laktozy",
    )
    assert need.created_at is not None


async def test_needs_for_same_product_are_merged(session, home):
    household, ala, ola, *_ = home

    first = await service.add_needs(
        session, household, ala, [NeedInput("mleko", Decimal(1), Unit.L)]
    )
    second = await service.add_needs(
        session, household, ola, [NeedInput(" Mleko ", Decimal(2), Unit.L)]
    )

    items = await items_by_name(session, household)
    assert list(items) == ["mleko"]
    assert [n.user.login for n in items["mleko"].needs] == ["ala", "ola"]
    assert [
        q.amount for q in aggregate_quantities((n.amount, n.unit) for n in items["mleko"].needs)
    ] == [Decimal(3)]
    assert (first[0].merged, second[0].merged) == (False, True)


async def test_need_without_amount(session, home):
    household, ala, *_ = home

    await service.add_needs(session, household, ala, [NeedInput("chleb")])

    (need,) = (await items_by_name(session, household))["chleb"].needs
    assert need.amount is None


async def test_unknown_product_without_category_goes_to_other(session, home):
    household, ala, *_ = home

    await service.add_needs(session, household, ala, [NeedInput("kwas cytrynowy")])

    assert (await items_by_name(session, household))["kwas cytrynowy"].category == Category.OTHER


async def test_known_product_reuses_remembered_category(session, home):
    household, ala, ola, *_ = home
    await service.add_needs(session, household, ala, [NeedInput("mleko", category=Category.DAIRY)])
    item_id = (await items_by_name(session, household))["mleko"].id
    await service.remove_item(session, household, item_id)

    await service.add_needs(session, household, ola, [NeedInput("Mleko")])

    assert (await items_by_name(session, household))["Mleko"].category == Category.DAIRY


async def test_category_memory_is_per_household(session, home):
    household, ala, _, other, ewa = home
    await service.add_needs(session, household, ala, [NeedInput("mleko", category=Category.DAIRY)])

    await service.add_needs(session, other, ewa, [NeedInput("mleko")])

    assert (await items_by_name(session, other))["mleko"].category == Category.OTHER


async def test_mark_and_unmark_bought(session, home):
    household, ala, ola, *_ = home
    await service.add_needs(session, household, ala, [NeedInput("mleko")])
    item = (await items_by_name(session, household))["mleko"]

    await service.set_bought(session, household, ola, [item.id], bought=True)
    item = (await items_by_name(session, household))["mleko"]
    assert item.bought_at is not None
    assert item.bought_by.login == "ola"

    await service.set_bought(session, household, ala, [item.id], bought=False)
    item = (await items_by_name(session, household))["mleko"]
    assert item.bought_at is None and item.bought_by is None


async def test_new_need_on_bought_item_makes_it_needed_again(session, home):
    household, ala, ola, *_ = home
    await service.add_needs(session, household, ala, [NeedInput("mleko")])
    item = (await items_by_name(session, household))["mleko"]
    await service.set_bought(session, household, ala, [item.id], bought=True)

    await service.add_needs(session, household, ola, [NeedInput("mleko")])

    assert (await items_by_name(session, household))["mleko"].bought_at is None


async def test_withdraw_own_need_keeps_item_with_other_needs(session, home):
    household, ala, ola, *_ = home
    await service.add_needs(session, household, ala, [NeedInput("mleko", Decimal(1), Unit.L)])
    await service.add_needs(session, household, ola, [NeedInput("mleko", Decimal(2), Unit.L)])
    ala_need = (await items_by_name(session, household))["mleko"].needs[0]

    await service.withdraw_need(session, household, ala, ala_need.id)

    (need,) = (await items_by_name(session, household))["mleko"].needs
    assert (need.user.login, need.amount) == ("ola", Decimal(2))


async def test_withdrawing_last_need_removes_item(session, home):
    household, ala, *_ = home
    await service.add_needs(session, household, ala, [NeedInput("chleb")])
    need = (await items_by_name(session, household))["chleb"].needs[0]

    await service.withdraw_need(session, household, ala, need.id)

    assert await items_by_name(session, household) == {}


async def test_cannot_change_or_withdraw_someone_elses_need(session, home):
    household, ala, ola, *_ = home
    await service.add_needs(session, household, ala, [NeedInput("chleb")])
    need = (await items_by_name(session, household))["chleb"].needs[0]

    with pytest.raises(Forbidden):
        await service.withdraw_need(session, household, ola, need.id)
    with pytest.raises(Forbidden):
        await service.update_need(session, household, ola, need.id, {"amount": Decimal(5)})


async def test_update_own_need(session, home):
    household, ala, *_ = home
    await service.add_needs(session, household, ala, [NeedInput("chleb")])
    need = (await items_by_name(session, household))["chleb"].needs[0]

    await service.update_need(
        session, household, ala, need.id, {"amount": Decimal(2), "unit": Unit.PCS}
    )

    need = (await items_by_name(session, household))["chleb"].needs[0]
    assert (need.amount, need.unit, need.note) == (Decimal(2), Unit.PCS, None)


async def test_remove_item_removes_all_needs(session, home):
    household, ala, ola, *_ = home
    await service.add_needs(session, household, ala, [NeedInput("chleb")])
    await service.add_needs(session, household, ola, [NeedInput("chleb")])
    item = (await items_by_name(session, household))["chleb"]

    await service.remove_item(session, household, item.id)

    assert await items_by_name(session, household) == {}


async def test_finish_shopping_moves_only_bought_items_to_history(session, home, purchase_history):
    household, ala, *_ = home
    await service.add_needs(session, household, ala, [NeedInput("mleko"), NeedInput("chleb")])
    milk = (await items_by_name(session, household))["mleko"]
    await service.set_bought(session, household, ala, [milk.id], bought=True)

    archived = await service.finish_shopping(session, household, ala)

    assert archived == 1
    assert list(await items_by_name(session, household)) == ["chleb"]
    (trip,) = await purchase_history(household.id)
    assert [i.name for i in trip.items] == ["mleko"]


async def test_history_keeps_who_when_category_requesters_and_amounts(
    session, home, purchase_history
):
    household, ala, ola, *_ = home
    await service.add_needs(
        session,
        household,
        ala,
        [NeedInput(" Mleko ", Decimal(2), Unit.L, "bez laktozy", Category.DAIRY)],
    )
    await service.add_needs(session, household, ola, [NeedInput("mleko", Decimal(1), Unit.L)])
    await service.set_bought(
        session, household, ola, [(await items_by_name(session, household))["Mleko"].id], True
    )
    milk = (await items_by_name(session, household))["Mleko"]
    bought_at = milk.bought_at
    requested_at = [n.created_at for n in milk.needs]

    await service.finish_shopping(session, household, ala)

    (trip,) = await purchase_history(household.id)
    assert (trip.household_id, trip.finished_by_id) == (household.id, ala.id)
    assert trip.finished_at >= bought_at
    (item,) = trip.items
    assert (item.name, item.normalized_name, item.category) == ("Mleko", "mleko", Category.DAIRY)
    assert (item.bought_by_id, item.bought_at) == (ola.id, bought_at)
    assert [(n.user_id, n.amount, n.unit, n.note) for n in item.needs] == [
        (ala.id, Decimal(2), Unit.L, "bez laktozy"),
        (ola.id, Decimal(1), Unit.L, None),
    ]
    assert [n.requested_at for n in item.needs] == requested_at


async def test_history_keeps_items_without_amount_and_check_off_order(
    session, home, purchase_history
):
    household, ala, ola, *_ = home
    await service.add_needs(
        session, household, ala, [NeedInput("chleb"), NeedInput("masło"), NeedInput("sól")]
    )
    items = await items_by_name(session, household)
    await service.set_bought(session, household, ola, [items["masło"].id], bought=True)
    await service.set_bought(session, household, ala, [items["chleb"].id], bought=True)

    await service.finish_shopping(session, household, ola)

    (trip,) = await purchase_history(household.id)
    assert [(i.name, i.bought_by_id) for i in trip.items] == [("masło", ola.id), ("chleb", ala.id)]
    assert trip.items[0].bought_at < trip.items[1].bought_at
    assert [(n.user_id, n.amount, n.unit) for n in trip.items[1].needs] == [(ala.id, None, None)]
    assert list(await items_by_name(session, household)) == ["sól"]


async def test_finish_shopping_without_bought_items_changes_nothing(
    session, home, purchase_history
):
    household, ala, *_ = home
    await service.add_needs(session, household, ala, [NeedInput("chleb")])

    assert await service.finish_shopping(session, household, ala) == 0

    assert list(await items_by_name(session, household)) == ["chleb"]
    assert await purchase_history() == []


async def test_each_finish_creates_separate_trip(session, home, purchase_history):
    household, ala, ola, *_ = home
    await service.add_needs(session, household, ala, [NeedInput("mleko")])
    milk = (await items_by_name(session, household))["mleko"]
    await service.set_bought(session, household, ala, [milk.id], bought=True)
    await service.finish_shopping(session, household, ala)

    # Ten sam produkt może wrócić na listę i zostać kupiony ponownie.
    await service.add_needs(session, household, ola, [NeedInput("mleko"), NeedInput("chleb")])
    items = await items_by_name(session, household)
    await service.set_bought(
        session, household, ola, [items["mleko"].id, items["chleb"].id], bought=True
    )
    await service.finish_shopping(session, household, ola)

    first, second = await purchase_history(household.id)
    assert (first.finished_by_id, [i.name for i in first.items]) == (ala.id, ["mleko"])
    assert (second.finished_by_id, sorted(i.name for i in second.items)) == (
        ola.id,
        ["chleb", "mleko"],
    )
    assert await items_by_name(session, household) == {}


async def test_history_is_scoped_to_household(session, home, purchase_history):
    household, ala, _, other, ewa = home
    await service.add_needs(session, household, ala, [NeedInput("mleko")])
    await service.add_needs(session, other, ewa, [NeedInput("kawa")])
    for home_, user in ((household, ala), (other, ewa)):
        (item,) = (await service.get_list(session, home_)).items
        await service.set_bought(session, home_, user, [item.id], bought=True)

    await service.finish_shopping(session, other, ewa)

    assert await purchase_history(household.id) == []
    (trip,) = await purchase_history(other.id)
    assert [i.name for i in trip.items] == ["kawa"]
    assert [i.name for i in (await service.get_list(session, household)).items] == ["mleko"]


async def test_operations_are_scoped_to_callers_household(session, home):
    household, ala, _, other, ewa = home
    await service.add_needs(session, household, ala, [NeedInput("mleko")])
    item = (await items_by_name(session, household))["mleko"]

    with pytest.raises(NotFound):
        await service.remove_item(session, other, item.id)
    with pytest.raises(NotFound):
        await service.set_bought(session, other, ewa, [item.id], bought=True)
    with pytest.raises(NotFound):
        await service.withdraw_need(session, other, ewa, item.needs[0].id)
    assert (await items_by_name(session, household))["mleko"].bought_at is None


async def test_removed_member_needs_stay_on_list(session, home):
    household, ala, ola, *_ = home
    await service.add_needs(session, household, ola, [NeedInput("mleko")])

    await households.remove_member(session, ala, household, ola.id)

    (need,) = (await items_by_name(session, household))["mleko"].needs
    assert need.user.login == "ola"


async def test_insert_if_absent_returns_existing_item_instead_of_failing(session, home):
    household, ala, *_ = home
    await service.add_needs(session, household, ala, [NeedInput("mleko", category=Category.DAIRY)])
    list_id = (await service.get_list(session, household)).id

    item, created = await service._insert_item_if_absent(
        session, list_id, "Mleko", "mleko", Category.OTHER
    )

    assert created is False
    assert (item.name, item.category) == ("mleko", Category.DAIRY)


async def test_concurrent_add_of_new_product_is_merged(session, home, monkeypatch):
    """Symulacja wyścigu: przy odczycie produktu jeszcze nie było, przy zapisie już jest."""
    household, ala, ola, *_ = home
    await service.add_needs(session, household, ala, [NeedInput("mleko", category=Category.DAIRY)])
    real_find = service._find_item
    calls = 0

    async def find_with_stale_first_read(*args):
        nonlocal calls
        calls += 1
        return None if calls == 1 else await real_find(*args)

    monkeypatch.setattr(service, "_find_item", find_with_stale_first_read)

    added = await service.add_needs(session, household, ola, [NeedInput("Mleko")])

    assert added[0].merged is True
    (item,) = (await service.get_list(session, household)).items
    assert [n.user.login for n in item.needs] == ["ala", "ola"]

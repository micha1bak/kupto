from collections.abc import AsyncIterator

from fastapi import APIRouter, Request, status
from fastapi.responses import StreamingResponse

from kupto.deps import CurrentHousehold, CurrentUser, NotifierDep, SessionDep, SettingsDep
from kupto.errors import DomainError
from kupto.lists import category_order, notifications, product_order, service, shopping_status
from kupto.lists.events import BrokerUnavailable, ListEventBroker
from kupto.lists.learned_order import learned_order
from kupto.lists.schemas import (
    CategoryMove,
    CategoryOrderEntry,
    ItemMove,
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
    """Wspólna lista gospodarstwa w kolejności kategorii i produktów danego użytkownika."""
    shopping_list = await service.get_list(session, household)
    learned = await learned_order(session, user)
    return list_out(
        shopping_list,
        await category_order.get_order(session, user, learned),
        await shopping_status.active_shoppers(session, household),
        await product_order.get_order(session, user, learned),
    )


@router.get("")
async def get_list(user: CurrentUser, household: CurrentHousehold, session: SessionDep) -> ListOut:
    return await _current_list(session, household, user)


class EventsUnavailable(DomainError):
    status_code = 503


# Ile czekamy na połączenie LISTEN przy otwieraniu strumienia, zanim klient wróci do pollingu.
BROKER_READY_TIMEOUT_SECONDS = 5.0
RECONNECT_DELAY_MS = 3000


@router.get("/events", response_class=StreamingResponse)
async def list_events(
    request: Request,
    user: CurrentUser,
    household: CurrentHousehold,
    session: SessionDep,
    settings: SettingsDep,
) -> StreamingResponse:
    """Strumień SSE: sygnał `list_changed`, gdy lista gospodarstwa (albo własna kolejność
    kategorii) się zmieni. Treść listy klient pobiera zwykłym `GET /api/list` (design D1)."""
    user_id, household_id = user.id, household.id
    # Strumień żyje długo — połączenie z puli bazy wraca od razu, zostaje tylko subskrypcja.
    await session.close()
    broker: ListEventBroker = request.app.state.list_events
    try:
        await broker.wait_ready(BROKER_READY_TIMEOUT_SECONDS)
    except BrokerUnavailable:
        raise EventsUnavailable("Zmiany listy na żywo są chwilowo niedostępne.") from None
    return StreamingResponse(
        _event_stream(broker, household_id, user_id, settings.list_events_heartbeat_seconds),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _event_stream(
    broker: ListEventBroker, household_id: int, user_id: int, heartbeat: float
) -> AsyncIterator[str]:
    # Subskrypcja dopiero w generatorze: `finally` sprząta ją także przy rozłączeniu klienta.
    try:
        subscription = broker.subscribe(household_id, user_id)
    except BrokerUnavailable:
        return  # nasłuch padł w międzyczasie — klient połączy się ponownie
    try:
        yield f"retry: {RECONNECT_DELAY_MS}\n\nevent: ready\ndata: {{}}\n\n"
        while True:
            changed = await subscription.wait(heartbeat)
            if subscription.closed:
                return
            yield "event: list_changed\ndata: {}\n\n" if changed else ": ping\n\n"
    finally:
        broker.unsubscribe(subscription)


@router.post("/needs", status_code=status.HTTP_201_CREATED)
async def add_need(
    payload: NeedCreate,
    user: CurrentUser,
    household: CurrentHousehold,
    session: SessionDep,
    notifier: NotifierDep,
) -> ListOut:
    await service.add_needs(session, household, user, [NeedInput(**payload.model_dump())])
    await notifications.items_added(session, notifier, household, user)
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
    user: CurrentUser, household: CurrentHousehold, session: SessionDep, notifier: NotifierDep
) -> ListOut:
    if await service.finish_shopping(session, household, user):
        await notifications.shopping_finished(session, notifier, household, user)
    return await _current_list(session, household, user)


# Status „robię zakupy” zalogowanego użytkownika; widać go w `shoppers` każdej odpowiedzi listy.


@router.post("/shopping")
async def start_shopping(
    user: CurrentUser, household: CurrentHousehold, session: SessionDep, notifier: NotifierDep
) -> ListOut:
    if await shopping_status.start(session, user):
        notifications.shopping_started(notifier, household, user)
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


# Kolejność produktów w kategorii — też per użytkownik, zapamiętana per produkt (nazwa).


@router.put("/items/{item_id}/order")
async def pin_item(
    item_id: int,
    payload: ItemMove,
    user: CurrentUser,
    household: CurrentHousehold,
    session: SessionDep,
) -> ListOut:
    await product_order.pin(session, household, user, item_id, payload.after, payload.before)
    return await _current_list(session, household, user)


@router.delete("/items/{item_id}/order")
async def unpin_item(
    item_id: int, user: CurrentUser, household: CurrentHousehold, session: SessionDep
) -> ListOut:
    await product_order.unpin(session, household, user, item_id)
    return await _current_list(session, household, user)

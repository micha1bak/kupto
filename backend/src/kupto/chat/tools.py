"""Narzędzia udostępniane modelowi.

Model wybiera tylko nazwę narzędzia i argumenty. Użytkownik i gospodarstwo pochodzą
z sesji (`ToolContext`), nigdy z argumentów, więc model może działać wyłącznie na liście
autora wiadomości. Błędy reguł wracają do modelu jako `{"error": ...}`, a nie jako wyjątki.
"""

import json
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from pydantic import ValidationError
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from kupto.errors import DomainError
from kupto.history import usual
from kupto.lists import notifications, service, shopping_status
from kupto.lists.schemas import NeedCreate, NeedUpdate, list_out
from kupto.lists.service import NeedInput
from kupto.models import Category, ChatPendingAction, Household, Unit, User
from kupto.push.notifier import Notifier

FINISH_SHOPPING = "finish_shopping"
MAX_USUAL_SUGGESTIONS = 10

_CATEGORIES = [c.value for c in Category]
_UNITS = [u.value for u in Unit]


def _nullable(schema: dict[str, Any]) -> dict[str, Any]:
    nullable = {**schema, "type": [schema["type"], "null"]}
    if "enum" in schema:
        nullable["enum"] = [*schema["enum"], None]
    return nullable


def _function(name: str, description: str, properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "name": name,
        "description": description,
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": list(properties),
            "additionalProperties": False,
        },
    }


_ID_LIST = {"type": "array", "items": {"type": "integer"}}

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    _function("get_list", "Zwraca aktualną listę zakupów gospodarstwa.", {}),
    _function(
        "add_needs",
        "Dodaje zapotrzebowania autora wiadomości. Używaj tylko dla konkretnych produktów, "
        "które użytkownik wskazał lub potwierdził.",
        {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Nazwa produktu po polsku, w mianowniku, "
                            "bez ilości, np. 'jogurt naturalny'.",
                        },
                        "amount": _nullable({"type": "number"}),
                        "unit": _nullable({"type": "string", "enum": _UNITS}),
                        "note": _nullable({"type": "string", "description": "Np. 'bez laktozy'."}),
                        "category": {"type": "string", "enum": _CATEGORIES},
                    },
                    "required": ["name", "amount", "unit", "note", "category"],
                    "additionalProperties": False,
                },
            }
        },
    ),
    _function(
        "update_need",
        "Zmienia własne zapotrzebowanie autora. Pole null oznacza brak zmiany.",
        {
            "need_id": {"type": "integer"},
            "amount": _nullable({"type": "number"}),
            "unit": _nullable({"type": "string", "enum": _UNITS}),
            "note": _nullable({"type": "string"}),
        },
    ),
    _function(
        "withdraw_need",
        "Wycofuje własne zapotrzebowanie autora.",
        {"need_id": {"type": "integer"}},
    ),
    _function("remove_item", "Usuwa całą pozycję z listy.", {"item_id": {"type": "integer"}}),
    _function("mark_bought", "Oznacza pozycje jako kupione.", {"item_ids": _ID_LIST}),
    _function("unmark_bought", "Cofa oznaczenie pozycji jako kupionych.", {"item_ids": _ID_LIST}),
    _function(
        "request_finish_shopping",
        "Prosi o potwierdzenie zakończenia zakupów (przeniesienia kupionych pozycji z listy "
        "do historii zakupów). Po wywołaniu zapytaj użytkownika o potwierdzenie.",
        {},
    ),
    _function(
        "confirm_finish_shopping",
        "Kończy zakupy. Działa tylko, gdy w poprzedniej wiadomości poproszono o potwierdzenie, "
        "a użytkownik właśnie je wyraził.",
        {},
    ),
    _function(
        "get_usual_missing",
        "Zwraca produkty, które gospodarstwo kupuje regularnie, a których teraz nie ma na "
        "liście (z typową ilością i jednostką). Tylko odczyt — niczego nie dodaje.",
        {},
    ),
    _function(
        "start_shopping",
        "Włącza status „robię zakupy” autora wiadomości — domownicy widzą, że jest w sklepie. "
        "Status sam wygasa po 3 godzinach. Nie zmienia pozycji listy.",
        {},
    ),
    _function(
        "stop_shopping",
        "Wyłącza status „robię zakupy” autora wiadomości. Nie zmienia pozycji listy.",
        {},
    ),
]

LIST_CHANGING_TOOLS = {
    "add_needs",
    "update_need",
    "withdraw_need",
    "remove_item",
    "mark_bought",
    "unmark_bought",
    "confirm_finish_shopping",
    # Status zakupów jest częścią odpowiedzi listy (`shoppers`), więc klient też ją odświeża.
    "start_shopping",
    "stop_shopping",
}


@dataclass
class ToolContext:
    session: AsyncSession
    household: Household
    user: User
    # Akcja oczekująca na potwierdzenie z poprzedniej tury (już usunięta z bazy na starcie tury).
    pending_action: str | None = None
    # Powiadomienia push o zakupach (#29–#31); bez niego (testy narzędzi, ewaluacje) nie idą.
    notifier: Notifier | None = None


@dataclass(frozen=True)
class ToolResult:
    output: dict[str, Any]
    list_changed: bool


async def execute_tool(ctx: ToolContext, name: str, arguments: str) -> ToolResult:
    handler = _HANDLERS.get(name)
    if handler is None:
        return ToolResult({"error": f"Nieznane narzędzie: {name}"}, list_changed=False)
    try:
        args = json.loads(arguments or "{}")
        output = await handler(ctx, **args)
    except (json.JSONDecodeError, TypeError) as exc:
        return ToolResult({"error": f"Nieprawidłowe argumenty: {exc}"}, list_changed=False)
    except ValidationError as exc:
        return ToolResult({"error": _validation_message(exc)}, list_changed=False)
    except DomainError as exc:
        # Serwisy sprawdzają reguły przed jakąkolwiek zmianą, więc nie ma czego wycofywać.
        return ToolResult({"error": exc.message}, list_changed=False)
    return ToolResult(output, list_changed=name in LIST_CHANGING_TOOLS and "error" not in output)


async def list_snapshot(ctx: ToolContext) -> dict[str, Any]:
    """Lista w zwięzłej postaci dla modelu — pochodna tej samej serializacji co REST API."""
    shopping_list = list_out(await service.get_list(ctx.session, ctx.household))
    return {
        "items": [
            {
                "item_id": item.id,
                "name": item.name,
                "category": item.category.value,
                "quantities": [_format_quantity(q.amount, q.unit) for q in item.quantities],
                "bought": item.bought,
                "needs": [
                    {
                        "need_id": n.id,
                        "requested_by": n.login,
                        "mine": n.user_id == ctx.user.id,
                        "amount": n.amount,
                        "unit": n.unit.value if n.unit else None,
                        "note": n.note,
                    }
                    for n in item.needs
                ],
            }
            for group in shopping_list.groups
            for item in group.items
        ],
        "shopping_now": [
            s.login for s in await shopping_status.active_shoppers(ctx.session, ctx.household)
        ],
    }


def _format_quantity(amount: float, unit: Unit | None) -> str:
    return f"{amount:g} {unit.value}" if unit else f"{amount:g}"


async def _get_list(ctx: ToolContext) -> dict[str, Any]:
    return await list_snapshot(ctx)


async def _add_needs(ctx: ToolContext, items: list[dict[str, Any]]) -> dict[str, Any]:
    inputs = [NeedInput(**NeedCreate.model_validate(item).model_dump()) for item in items]
    added = await service.add_needs(ctx.session, ctx.household, ctx.user, inputs)
    if ctx.notifier is not None:
        await notifications.items_added(ctx.session, ctx.notifier, ctx.household, ctx.user)
    return {
        "added": [
            {"name": a.item_name, "category": a.category.value, "already_on_list": a.merged}
            for a in added
        ]
    }


async def _update_need(
    ctx: ToolContext,
    need_id: int,
    amount: float | None,
    unit: str | None,
    note: str | None,
) -> dict[str, Any]:
    provided = {
        k: v for k, v in {"amount": amount, "unit": unit, "note": note}.items() if v is not None
    }
    changes = NeedUpdate.model_validate(provided).model_dump(include=set(provided))
    await service.update_need(ctx.session, ctx.household, ctx.user, need_id, changes)
    return {"status": "updated"}


async def _withdraw_need(ctx: ToolContext, need_id: int) -> dict[str, Any]:
    await service.withdraw_need(ctx.session, ctx.household, ctx.user, need_id)
    return {"status": "withdrawn"}


async def _remove_item(ctx: ToolContext, item_id: int) -> dict[str, Any]:
    name = await service.remove_item(ctx.session, ctx.household, item_id)
    return {"removed": name}


async def _mark_bought(ctx: ToolContext, item_ids: list[int]) -> dict[str, Any]:
    names = await service.set_bought(ctx.session, ctx.household, ctx.user, item_ids, bought=True)
    return {"marked_bought": names}


async def _unmark_bought(ctx: ToolContext, item_ids: list[int]) -> dict[str, Any]:
    names = await service.set_bought(ctx.session, ctx.household, ctx.user, item_ids, bought=False)
    return {"unmarked": names}


async def _request_finish_shopping(ctx: ToolContext) -> dict[str, Any]:
    await ctx.session.merge(ChatPendingAction(user_id=ctx.user.id, action=FINISH_SHOPPING))
    await ctx.session.commit()
    snapshot = await list_snapshot(ctx)
    bought = [i["name"] for i in snapshot["items"] if i["bought"]]
    return {"status": "confirmation_required", "bought_items_to_archive": bought}


async def _confirm_finish_shopping(ctx: ToolContext) -> dict[str, Any]:
    if ctx.pending_action != FINISH_SHOPPING:
        return {
            "error": "Brak oczekującej prośby o potwierdzenie. Najpierw wywołaj "
            "request_finish_shopping i zapytaj użytkownika."
        }
    ctx.pending_action = None
    archived = await service.finish_shopping(ctx.session, ctx.household, ctx.user)
    if archived and ctx.notifier is not None:
        await notifications.shopping_finished(ctx.session, ctx.notifier, ctx.household, ctx.user)
    return {"status": "finished", "archived_items": archived}


async def _get_usual_missing(ctx: ToolContext) -> dict[str, Any]:
    suggestions = await usual.usual_missing(ctx.session, ctx.household)
    day = timedelta(days=1)
    return {
        "usual_missing": [
            {
                "name": s.name,
                "category": s.category.value,
                "typical_amount": float(s.amount) if s.amount is not None else None,
                "unit": s.unit.value if s.unit else None,
                "bought_times": s.times_bought,
                "every_days": round(s.typical_interval / day, 1),
                "days_since_last": round(s.since_last / day, 1),
            }
            for s in suggestions[:MAX_USUAL_SUGGESTIONS]
        ]
    }


async def _start_shopping(ctx: ToolContext) -> dict[str, Any]:
    started = await shopping_status.start(ctx.session, ctx.user)
    if started and ctx.notifier is not None:
        notifications.shopping_started(ctx.notifier, ctx.household, ctx.user)
    others = [
        s.login
        for s in await shopping_status.active_shoppers(ctx.session, ctx.household)
        if s.user_id != ctx.user.id
    ]
    return {
        "status": "shopping",
        "already_shopping": not started,
        "expires_in_hours": shopping_status.SHOPPING_STATUS_TTL.total_seconds() / 3600,
        "others_shopping": others,
    }


async def _stop_shopping(ctx: ToolContext) -> dict[str, Any]:
    was_active = await shopping_status.stop(ctx.session, ctx.user)
    return {"status": "stopped" if was_active else "was_not_shopping"}


async def clear_pending_action(session: AsyncSession, user: User) -> str | None:
    """Pobiera i kasuje oczekującą akcję — potwierdzenie jest ważne tylko w następnej turze."""
    pending = await session.get(ChatPendingAction, user.id)
    if pending is None:
        return None
    action = pending.action
    await session.execute(delete(ChatPendingAction).where(ChatPendingAction.user_id == user.id))
    await session.commit()
    return action


def _validation_message(exc: ValidationError) -> str:
    problems = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())
    return f"Nieprawidłowe dane: {problems}"


_HANDLERS = {
    "get_list": _get_list,
    "add_needs": _add_needs,
    "update_need": _update_need,
    "withdraw_need": _withdraw_need,
    "remove_item": _remove_item,
    "mark_bought": _mark_bought,
    "unmark_bought": _unmark_bought,
    "request_finish_shopping": _request_finish_shopping,
    "confirm_finish_shopping": _confirm_finish_shopping,
    "get_usual_missing": _get_usual_missing,
    "start_shopping": _start_shopping,
    "stop_shopping": _stop_shopping,
}

assert set(_HANDLERS) == {t["name"] for t in TOOL_DEFINITIONS}

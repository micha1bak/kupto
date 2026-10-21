"""Narzędzia udostępniane modelowi.

Model wybiera tylko nazwę narzędzia i argumenty. Użytkownik i gospodarstwo pochodzą
z sesji (`ToolContext`), nigdy z argumentów, więc model może działać wyłącznie na liście
autora wiadomości. Błędy reguł wracają do modelu jako `{"error": ...}`, a nie jako wyjątki.
"""

import json
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from kupto.errors import DomainError
from kupto.lists import service
from kupto.lists.quantities import aggregate_quantities
from kupto.lists.schemas import NeedCreate, NeedUpdate
from kupto.lists.service import NeedInput
from kupto.models import Category, ChatPendingAction, Household, Unit, User

FINISH_SHOPPING = "finish_shopping"

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
        "Prosi o potwierdzenie zakończenia zakupów (usunięcia kupionych pozycji). "
        "Po wywołaniu zapytaj użytkownika o potwierdzenie.",
        {},
    ),
    _function(
        "confirm_finish_shopping",
        "Kończy zakupy. Działa tylko, gdy w poprzedniej wiadomości poproszono o potwierdzenie, "
        "a użytkownik właśnie je wyraził.",
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
}


@dataclass
class ToolContext:
    session: AsyncSession
    household: Household
    user: User
    # Akcja oczekująca na potwierdzenie z poprzedniej tury (już usunięta z bazy na starcie tury).
    pending_action: str | None = None


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
    shopping_list = await service.get_list(ctx.session, ctx.household)
    items = sorted(shopping_list.items, key=lambda i: (list(Category).index(i.category), i.name))
    return {
        "items": [
            {
                "item_id": item.id,
                "name": item.name,
                "category": item.category.value,
                "quantities": [
                    f"{q.amount} {q.unit.value if q.unit else ''}".strip()
                    for q in aggregate_quantities((n.amount, n.unit) for n in item.needs)
                ],
                "bought": item.bought_at is not None,
                "needs": [
                    {
                        "need_id": n.id,
                        "requested_by": n.user.login if n.user else None,
                        "mine": n.user_id == ctx.user.id,
                        "amount": float(n.amount) if n.amount is not None else None,
                        "unit": n.unit.value if n.unit else None,
                        "note": n.note,
                    }
                    for n in item.needs
                ],
            }
            for item in items
        ]
    }


async def _get_list(ctx: ToolContext) -> dict[str, Any]:
    return await list_snapshot(ctx)


async def _add_needs(ctx: ToolContext, items: list[dict[str, Any]]) -> dict[str, Any]:
    inputs = [NeedInput(**NeedCreate.model_validate(item).model_dump()) for item in items]
    added = await service.add_needs(ctx.session, ctx.household, ctx.user, inputs)
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
    return {"status": "confirmation_required", "bought_items_to_remove": bought}


async def _confirm_finish_shopping(ctx: ToolContext) -> dict[str, Any]:
    if ctx.pending_action != FINISH_SHOPPING:
        return {
            "error": "Brak oczekującej prośby o potwierdzenie. Najpierw wywołaj "
            "request_finish_shopping i zapytaj użytkownika."
        }
    ctx.pending_action = None
    removed = await service.finish_shopping(ctx.session, ctx.household)
    return {"status": "finished", "removed_items": removed}


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
}

assert set(_HANDLERS) == {t["name"] for t in TOOL_DEFINITIONS}

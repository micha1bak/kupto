import json
import logging
import math
import time
from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from kupto.chat.agent import AgentStats, Delta, ListChanged, run_agent
from kupto.chat.llm import LLMClient, LLMUnavailable, OpenAIResponsesClient
from kupto.chat.prompt import build_input, build_instructions
from kupto.chat.tools import ToolContext, clear_pending_action, list_snapshot
from kupto.config import Settings
from kupto.db import utcnow
from kupto.deps import CurrentHousehold, CurrentUser, SessionDep, SettingsDep
from kupto.errors import TooManyRequests
from kupto.households import preferences
from kupto.lists import events
from kupto.meal_plan import service as meal_plan
from kupto.models import ChatMessage, ChatPendingAction, Household, User, display_name
from kupto.push.notifier import Notifier

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 8000  # mieści wklejony przepis z opisem przygotowania
# Ile ostatnich wiadomości wątku gospodarstwa dostaje klient (bez paginacji, design D1).
THREAD_LIMIT = 200
UNAVAILABLE_MESSAGE = (
    "Asystent jest chwilowo niedostępny. Spróbuj ponownie za chwilę — "
    "listę możesz w tym czasie edytować ręcznie."
)


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH, pattern=r"\S")


class Author(BaseModel):
    id: int
    name: str  # imię, a w koncie bez imienia login


class MessageOut(BaseModel):
    id: int
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    author: Author | None  # None dla odpowiedzi asystenta
    mine: bool  # wiadomość bieżącego użytkownika (odpowiedzi asystenta — nigdy)


def message_out(message: ChatMessage, user: User) -> MessageOut:
    is_user = message.role == "user"
    return MessageOut(
        id=message.id,
        role=message.role,
        content=message.content,
        created_at=message.created_at,
        author=Author(id=message.user.id, name=display_name(message.user)) if is_user else None,
        mine=is_user and message.user_id == user.id,
    )


def get_llm_client(request: Request) -> LLMClient:
    if request.app.state.llm_client is None:
        settings: Settings = request.app.state.settings
        request.app.state.llm_client = OpenAIResponsesClient(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.openai_model,
            timeout=settings.openai_timeout_seconds,
        )
    return request.app.state.llm_client


async def check_rate_limit(session: AsyncSession, user: User, settings: Settings) -> None:
    window_start = utcnow() - timedelta(hours=1)
    count, oldest = (
        await session.execute(
            select(func.count(ChatMessage.id), func.min(ChatMessage.created_at)).where(
                ChatMessage.user_id == user.id,
                ChatMessage.role == "user",
                ChatMessage.created_at > window_start,
            )
        )
    ).one()
    if count >= settings.chat_rate_limit_per_hour:
        retry_after = max(1, math.ceil((oldest - window_start).total_seconds()))
        raise TooManyRequests(
            f"Przekroczono limit {settings.chat_rate_limit_per_hour} wiadomości na godzinę. "
            f"Spróbuj ponownie za {math.ceil(retry_after / 60)} min.",
            retry_after=retry_after,
        )


def _thread(household: Household, limit: int) -> Select[tuple[ChatMessage]]:
    """Ostatnie `limit` wiadomości wątku gospodarstwa (bez archiwum prywatnych rozmów, D2),
    od najnowszych — wołający odwraca kolejność."""
    return (
        select(ChatMessage)
        .options(selectinload(ChatMessage.user))
        .where(ChatMessage.household_id == household.id, ChatMessage.private.is_(False))
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(limit)
    )


async def _model_history(
    session: AsyncSession, household: Household, settings: Settings
) -> list[ChatMessage]:
    """Kontekst modelu: ostatnie wiadomości wątku z ostatnich `chat_history_max_age_hours` (D5)."""
    since = utcnow() - timedelta(hours=settings.chat_history_max_age_hours)
    statement = _thread(household, max(settings.chat_history_limit, 1)).where(
        ChatMessage.created_at > since
    )
    return list(reversed((await session.scalars(statement)).all()))


@router.get("/messages")
async def get_messages(
    user: CurrentUser, household: CurrentHousehold, session: SessionDep
) -> list[MessageOut]:
    statement = _thread(household, THREAD_LIMIT)
    if user.chat_hidden_before is not None:
        statement = statement.where(ChatMessage.created_at > user.chat_hidden_before)
    messages = reversed((await session.scalars(statement)).all())
    return [message_out(m, user) for m in messages]


@router.delete("/messages", status_code=status.HTTP_204_NO_CONTENT)
async def hide_messages(
    user: CurrentUser, household: CurrentHousehold, session: SessionDep
) -> None:
    """Ukrywa dotychczasowy wątek tylko u bieżącego użytkownika (D8) — wiadomości zostają
    dla domowników i modelu. Własna oczekująca akcja przepada, jak przy dawnym czyszczeniu."""
    user.chat_hidden_before = utcnow()
    await session.execute(delete(ChatPendingAction).where(ChatPendingAction.user_id == user.id))
    await session.commit()


@router.post("/messages")
async def send_message(
    payload: MessageCreate,
    request: Request,
    user: CurrentUser,
    household: CurrentHousehold,
    session: SessionDep,
    settings: SettingsDep,
    llm: Annotated[LLMClient, Depends(get_llm_client)],
) -> StreamingResponse:
    # Walidacja i limit przed otwarciem strumienia, by zwrócić zwykłe kody 422/429.
    await check_rate_limit(session, user, settings)
    session.add(
        ChatMessage(
            user_id=user.id, household_id=household.id, role="user", content=payload.content
        )
    )
    await events.chat_changed(session, household.id)
    await session.commit()
    reply = _stream_reply(
        request.app.state.sessionmaker,
        llm,
        settings,
        request.app.state.notifier,
        user.id,
        household.id,
    )
    return StreamingResponse(
        reply,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _stream_reply(
    sessionmaker,
    llm: LLMClient,
    settings: Settings,
    notifier: Notifier,
    user_id: int,
    household_id: int,
) -> AsyncIterator[str]:
    # Strumień żyje dłużej niż żądanie, więc używa własnej sesji bazy.
    async with sessionmaker() as session:
        user = await session.get(User, user_id)
        household = await session.get(Household, household_id)
        ctx = ToolContext(session, household, user, notifier=notifier)
        ctx.pending_action = await clear_pending_action(session, user)
        instructions = build_instructions(
            display_name(user),
            household.name,
            await list_snapshot(ctx),
            ctx.pending_action,
            preferences.for_model(await preferences.load(session, household)),
            meal_plan.today(),
        )
        conversation = build_input(
            await _model_history(session, household, settings), settings.chat_history_limit
        )
        reply: list[str] = []
        stats = AgentStats()
        started = time.monotonic()
        outcome = "cancelled"  # klient zamknął strumień przed końcem odpowiedzi
        try:
            async for event in run_agent(
                llm,
                ctx,
                instructions=instructions,
                input=conversation,
                max_tool_rounds=settings.chat_max_tool_rounds,
                stats=stats,
            ):
                if isinstance(event, Delta):
                    reply.append(event.text)
                    yield _sse("delta", {"text": event.text})
                elif isinstance(event, ListChanged):
                    yield _sse("list_changed", {})
            outcome = "ok"
        except LLMUnavailable as exc:
            outcome = "llm_unavailable"
            logger.warning(
                "Model niedostępny: %s",
                exc,
                extra={"user_id": user_id, "household_id": household_id},
            )
            yield _sse("error", {"message": UNAVAILABLE_MESSAGE})
        except Exception:
            outcome = "error"
            logger.exception(
                "Nieoczekiwany błąd podczas obsługi wiadomości czatu",
                extra={"user_id": user_id, "household_id": household_id},
            )
            await session.rollback()
            yield _sse("error", {"message": UNAVAILABLE_MESSAGE})
        finally:
            _log_usage(settings, stats, outcome, time.monotonic() - started, user_id, household_id)
        text = "".join(reply).strip()
        if text:
            session.add(
                ChatMessage(
                    user_id=user_id, household_id=household_id, role="assistant", content=text
                )
            )
            await events.chat_changed(session, household_id)
            await session.commit()
        yield _sse("done", {})


def _log_usage(
    settings: Settings,
    stats: AgentStats,
    outcome: str,
    duration: float,
    user_id: int,
    household_id: int,
) -> None:
    """Zdarzenie `llm_usage` dla podsumowań kosztów (deploy/kupto-usage.sh) — bez treści."""
    logger.info(
        "Zużycie modelu: %d wej. / %d wyj. tokenów",
        stats.input_tokens,
        stats.output_tokens,
        extra={
            "event": "llm_usage",
            "outcome": outcome,
            "model": settings.openai_model,
            "user_id": user_id,
            "household_id": household_id,
            "input_tokens": stats.input_tokens,
            "output_tokens": stats.output_tokens,
            "cached_tokens": stats.cached_tokens,
            "reasoning_tokens": stats.reasoning_tokens,
            "model_calls": stats.model_calls,
            "tool_rounds": stats.tool_rounds,
            "tool_calls": stats.tool_calls,
            "duration_ms": round(duration * 1000),
        },
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

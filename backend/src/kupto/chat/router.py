import json
import logging
import math
from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from kupto.chat.agent import Delta, ListChanged, run_agent
from kupto.chat.llm import LLMClient, LLMUnavailable, OpenAIResponsesClient
from kupto.chat.prompt import build_input, build_instructions
from kupto.chat.tools import ToolContext, clear_pending_action, list_snapshot
from kupto.config import Settings
from kupto.db import utcnow
from kupto.deps import CurrentHousehold, CurrentUser, SessionDep, SettingsDep
from kupto.errors import TooManyRequests
from kupto.models import ChatMessage, ChatPendingAction, Household, User

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 2000
UNAVAILABLE_MESSAGE = (
    "Asystent jest chwilowo niedostępny. Spróbuj ponownie za chwilę — "
    "listę możesz w tym czasie edytować ręcznie."
)


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH, pattern=r"\S")


class MessageOut(BaseModel):
    id: int
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


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


async def _history(session: AsyncSession, user: User, household: Household) -> list[ChatMessage]:
    result = await session.scalars(
        select(ChatMessage)
        .where(ChatMessage.user_id == user.id, ChatMessage.household_id == household.id)
        .order_by(ChatMessage.created_at, ChatMessage.id)
    )
    return list(result)


@router.get("/messages")
async def get_messages(
    user: CurrentUser, household: CurrentHousehold, session: SessionDep
) -> list[MessageOut]:
    return [
        MessageOut.model_validate(m, from_attributes=True)
        for m in await _history(session, user, household)
    ]


@router.delete("/messages", status_code=status.HTTP_204_NO_CONTENT)
async def clear_messages(
    user: CurrentUser, household: CurrentHousehold, session: SessionDep
) -> None:
    await session.execute(
        delete(ChatMessage).where(
            ChatMessage.user_id == user.id, ChatMessage.household_id == household.id
        )
    )
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
    await session.commit()
    events = _stream_reply(request.app.state.sessionmaker, llm, settings, user.id, household.id)
    return StreamingResponse(
        events,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _stream_reply(
    sessionmaker, llm: LLMClient, settings: Settings, user_id: int, household_id: int
) -> AsyncIterator[str]:
    # Strumień żyje dłużej niż żądanie, więc używa własnej sesji bazy.
    async with sessionmaker() as session:
        user = await session.get(User, user_id)
        household = await session.get(Household, household_id)
        ctx = ToolContext(session, household, user)
        ctx.pending_action = await clear_pending_action(session, user)
        instructions = build_instructions(
            user.login, household.name, await list_snapshot(ctx), ctx.pending_action
        )
        conversation = build_input(
            await _history(session, user, household), settings.chat_history_limit
        )
        reply: list[str] = []
        try:
            async for event in run_agent(
                llm,
                ctx,
                instructions=instructions,
                input=conversation,
                max_tool_rounds=settings.chat_max_tool_rounds,
            ):
                if isinstance(event, Delta):
                    reply.append(event.text)
                    yield _sse("delta", {"text": event.text})
                elif isinstance(event, ListChanged):
                    yield _sse("list_changed", {})
        except LLMUnavailable as exc:
            logger.warning("Model niedostępny: %s", exc)
            yield _sse("error", {"message": UNAVAILABLE_MESSAGE})
        except Exception:
            logger.exception("Nieoczekiwany błąd podczas obsługi wiadomości czatu")
            await session.rollback()
            yield _sse("error", {"message": UNAVAILABLE_MESSAGE})
        text = "".join(reply).strip()
        if text:
            session.add(
                ChatMessage(
                    user_id=user_id, household_id=household_id, role="assistant", content=text
                )
            )
            await session.commit()
        yield _sse("done", {})


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

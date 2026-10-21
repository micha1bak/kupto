"""Warstwa dostępu do modelu językowego.

Reszta aplikacji zna tylko protokół `LLMClient` i zdarzenia `TextDelta`/`ToolCall`,
dzięki czemu w testach można podstawić `FakeLLMClient`, a dostawcę zmienić w jednym miejscu.
"""

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

import openai


@dataclass(frozen=True)
class TextDelta:
    text: str


@dataclass(frozen=True)
class ToolCall:
    call_id: str
    name: str
    arguments: str  # JSON


LLMEvent = TextDelta | ToolCall


class LLMUnavailable(Exception):
    """Model nie odpowiedział poprawnie (błąd API, limit czasu, przerwana odpowiedź)."""


class LLMClient(Protocol):
    def stream(
        self, *, instructions: str, input: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> AsyncIterator[LLMEvent]: ...


class OpenAIResponsesClient:
    def __init__(self, *, api_key: str, model: str, timeout: float, base_url: str = ""):
        self._client = openai.AsyncOpenAI(
            api_key=api_key or "missing", base_url=base_url or None, timeout=timeout
        )
        self._model = model

    async def stream(
        self, *, instructions: str, input: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> AsyncIterator[LLMEvent]:
        try:
            response = await self._client.responses.create(
                model=self._model,
                instructions=instructions,
                input=input,
                tools=tools,
                store=False,
                stream=True,
            )
            async for event in response:
                mapped = map_stream_event(event)
                if mapped is not None:
                    yield mapped
        except openai.OpenAIError as exc:
            raise LLMUnavailable(str(exc)) from exc


def map_stream_event(event: Any) -> LLMEvent | None:
    """Tłumaczy zdarzenie strumienia Responses API na zdarzenie wewnętrzne (lub je pomija)."""
    match event.type:
        case "response.output_text.delta":
            return TextDelta(event.delta)
        case "response.output_item.done" if event.item.type == "function_call":
            return ToolCall(event.item.call_id, event.item.name, event.item.arguments)
        case "response.failed" | "response.incomplete" | "error":
            raise LLMUnavailable(f"Odpowiedź modelu przerwana: {event.type}")
    return None


@dataclass
class FakeLLMClient:
    """Skryptowany model do testów: każde wywołanie `stream` odtwarza kolejną rundę.

    Runda to lista zdarzeń albo wyjątek (np. `LLMUnavailable`) do rzucenia.
    """

    rounds: list[Sequence[LLMEvent] | Exception]
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def stream(
        self, *, instructions: str, input: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> AsyncIterator[LLMEvent]:
        self.calls.append(
            {"instructions": instructions, "input": [dict(i) for i in input], "tools": tools}
        )
        if not self.rounds:
            raise AssertionError("FakeLLMClient: brak zaplanowanej rundy")
        current = self.rounds.pop(0)
        if isinstance(current, Exception):
            raise current
        for event in current:
            yield event

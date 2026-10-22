import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from kupto.chat.llm import LLMClient, TextDelta, ToolCall, Usage
from kupto.chat.tools import TOOL_DEFINITIONS, ToolContext, execute_tool


@dataclass(frozen=True)
class Delta:
    text: str


@dataclass(frozen=True)
class ListChanged:
    pass


AgentEvent = Delta | ListChanged


@dataclass
class AgentStats:
    """Liczniki jednej tury czatu do logu zużycia (bez treści rozmowy)."""

    model_calls: int = 0
    tool_rounds: int = 0
    tool_calls: list[str] = field(default_factory=list)  # nazwy wywołanych narzędzi
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0

    def add_usage(self, usage: Usage) -> None:
        self.input_tokens += usage.input_tokens
        self.output_tokens += usage.output_tokens
        self.cached_tokens += usage.cached_tokens
        self.reasoning_tokens += usage.reasoning_tokens


async def run_agent(
    llm: LLMClient,
    ctx: ToolContext,
    *,
    instructions: str,
    input: list[dict[str, Any]],
    max_tool_rounds: int,
    stats: AgentStats | None = None,
) -> AsyncIterator[AgentEvent]:
    """Pętla: model → narzędzia → wyniki z powrotem do modelu, aż model odpowie bez narzędzi.

    Po `max_tool_rounds` rundach z narzędziami model dostaje ostatnie wywołanie bez narzędzi,
    więc musi odpowiedzieć tekstem. Zużycie tokenów i liczba rund trafiają do `stats` (także gdy
    tura przerwie się błędem).
    """
    stats = stats if stats is not None else AgentStats()
    conversation = list(input)
    text_emitted = False
    for round_number in range(max_tool_rounds + 1):
        tools = TOOL_DEFINITIONS if round_number < max_tool_rounds else []
        calls: list[ToolCall] = []
        round_text: list[str] = []
        stats.model_calls += 1
        async for event in llm.stream(instructions=instructions, input=conversation, tools=tools):
            if isinstance(event, TextDelta):
                if not round_text and text_emitted:
                    yield Delta("\n\n")  # oddziel tekst kolejnej rundy od poprzedniej
                round_text.append(event.text)
                text_emitted = True
                yield Delta(event.text)
            elif isinstance(event, Usage):
                stats.add_usage(event)
            else:
                calls.append(event)
        if not calls:
            return
        stats.tool_rounds += 1
        if round_text:
            # Model musi widzieć, co już napisał w tej turze — inaczej to powtarza.
            conversation.append({"role": "assistant", "content": "".join(round_text)})
        for call in calls:
            stats.tool_calls.append(call.name)
            result = await execute_tool(ctx, call.name, call.arguments)
            if result.list_changed:
                yield ListChanged()
            conversation.append(
                {
                    "type": "function_call",
                    "call_id": call.call_id,
                    "name": call.name,
                    "arguments": call.arguments,
                }
            )
            conversation.append(
                {
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": _json(result.output),
                }
            )


def _json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from kupto.chat.llm import LLMClient, TextDelta, ToolCall
from kupto.chat.tools import TOOL_DEFINITIONS, ToolContext, execute_tool


@dataclass(frozen=True)
class Delta:
    text: str


@dataclass(frozen=True)
class ListChanged:
    pass


AgentEvent = Delta | ListChanged


async def run_agent(
    llm: LLMClient,
    ctx: ToolContext,
    *,
    instructions: str,
    input: list[dict[str, Any]],
    max_tool_rounds: int,
) -> AsyncIterator[AgentEvent]:
    """Pętla: model → narzędzia → wyniki z powrotem do modelu, aż model odpowie bez narzędzi.

    Po `max_tool_rounds` rundach z narzędziami model dostaje ostatnie wywołanie bez narzędzi,
    więc musi odpowiedzieć tekstem.
    """
    conversation = list(input)
    text_emitted = False
    for round_number in range(max_tool_rounds + 1):
        tools = TOOL_DEFINITIONS if round_number < max_tool_rounds else []
        calls: list[ToolCall] = []
        round_text: list[str] = []
        async for event in llm.stream(instructions=instructions, input=conversation, tools=tools):
            if isinstance(event, TextDelta):
                if not round_text and text_emitted:
                    yield Delta("\n\n")  # oddziel tekst kolejnej rundy od poprzedniej
                round_text.append(event.text)
                text_emitted = True
                yield Delta(event.text)
            else:
                calls.append(event)
        if not calls:
            return
        if round_text:
            # Model musi widzieć, co już napisał w tej turze — inaczej to powtarza.
            conversation.append({"role": "assistant", "content": "".join(round_text)})
        for call in calls:
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

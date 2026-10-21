import pytest
from openai.types.responses import (
    ResponseFunctionToolCall,
    ResponseOutputItemDoneEvent,
    ResponseTextDeltaEvent,
)

from kupto.chat.llm import (
    FakeLLMClient,
    LLMUnavailable,
    TextDelta,
    ToolCall,
    map_stream_event,
)


def test_text_delta_event_is_mapped():
    event = ResponseTextDeltaEvent(
        type="response.output_text.delta",
        delta="Dodałem ",
        item_id="msg_1",
        output_index=0,
        content_index=0,
        sequence_number=3,
        logprobs=[],
    )

    assert map_stream_event(event) == TextDelta("Dodałem ")


def test_function_call_item_done_is_mapped():
    event = ResponseOutputItemDoneEvent(
        type="response.output_item.done",
        output_index=0,
        sequence_number=7,
        item=ResponseFunctionToolCall(
            type="function_call",
            call_id="call_1",
            name="add_needs",
            arguments='{"items": []}',
            id="fc_1",
            status="completed",
        ),
    )

    assert map_stream_event(event) == ToolCall("call_1", "add_needs", '{"items": []}')


@pytest.mark.parametrize("event_type", ["response.failed", "response.incomplete", "error"])
def test_failure_events_raise(event_type):
    class Event:
        type = event_type

    with pytest.raises(LLMUnavailable):
        map_stream_event(Event())


def test_other_events_are_ignored():
    class Event:
        type = "response.created"

    assert map_stream_event(Event()) is None


async def test_fake_client_replays_rounds_and_records_calls():
    fake = FakeLLMClient(
        rounds=[[TextDelta("a"), ToolCall("c", "get_list", "{}")], [TextDelta("b")]]
    )

    first = [e async for e in fake.stream(instructions="i", input=[{"role": "user"}], tools=[])]
    second = [e async for e in fake.stream(instructions="i", input=[], tools=[])]

    assert first == [TextDelta("a"), ToolCall("c", "get_list", "{}")]
    assert second == [TextDelta("b")]
    assert fake.calls[0]["input"] == [{"role": "user"}]


async def test_fake_client_can_raise():
    fake = FakeLLMClient(rounds=[LLMUnavailable("boom")])

    with pytest.raises(LLMUnavailable):
        [e async for e in fake.stream(instructions="", input=[], tools=[])]

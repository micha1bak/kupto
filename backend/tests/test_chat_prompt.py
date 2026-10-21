from kupto.chat.prompt import build_input, build_instructions
from kupto.models import ChatMessage


def test_instructions_contain_rules_user_and_current_list():
    snapshot = {"items": [{"item_id": 1, "name": "mleko"}]}

    instructions = build_instructions("ala", "Dom", snapshot)

    assert "asystentem zakupowym" in instructions
    assert "„ala”" in instructions and "„Dom”" in instructions
    assert '"name": "mleko"' in instructions


def test_pending_finish_shopping_is_stated_in_instructions():
    without = build_instructions("ala", "Dom", {"items": []})
    with_pending = build_instructions("ala", "Dom", {"items": []}, "finish_shopping")

    assert "confirm_finish_shopping; nie pytaj ponownie" not in without
    assert "confirm_finish_shopping; nie pytaj ponownie" in with_pending


def test_input_is_trimmed_to_most_recent_messages():
    history = [
        ChatMessage(role="user" if i % 2 == 0 else "assistant", content=f"m{i}") for i in range(30)
    ]

    result = build_input(history, limit=20)

    assert len(result) == 20
    assert result[0] == {"role": "user", "content": "m10"}
    assert result[-1] == {"role": "assistant", "content": "m29"}


def test_input_keeps_everything_when_history_is_short():
    history = [ChatMessage(role="user", content="cześć")]

    assert build_input(history, limit=20) == [{"role": "user", "content": "cześć"}]

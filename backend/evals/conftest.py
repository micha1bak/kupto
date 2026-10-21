import asyncio
import json
import os
import time

import pytest

from kupto.chat.llm import OpenAIResponsesClient
from kupto.config import Settings
from tests.conftest import *  # noqa: F403  (wspólne fixtures: baza, aplikacja, użytkownicy)


@pytest.fixture
def llm_client():
    # Zmienne środowiskowe albo backend/.env (OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL).
    # JWT_SECRET nie jest tu używany (aplikację tworzy fixture `settings`), ale jest wymagany.
    config = Settings(jwt_secret="x" * 32)
    if not config.openai_api_key:
        pytest.skip("Ewaluacje wymagają OPENAI_API_KEY")
    return OpenAIResponsesClient(
        api_key=config.openai_api_key,
        base_url=config.openai_base_url,
        model=config.openai_model,
        timeout=120,
    )


# Minimalny odstęp między wiadomościami do asystenta — dla dostawców z niskim limitem tokenów
# na minutę (np. darmowy Groq), by wyniki mierzyły model, a nie limity. Domyślnie bez pauzy.
EVAL_DELAY_SECONDS = float(os.environ.get("EVAL_DELAY_SECONDS", "0"))
_last_message_at = 0.0


@pytest.fixture
def chat():
    """Wysyła wiadomość i zwraca pełny tekst odpowiedzi asystenta."""

    async def send(client, content: str) -> str:
        global _last_message_at
        wait = _last_message_at + EVAL_DELAY_SECONDS - time.monotonic()
        if wait > 0:
            await asyncio.sleep(wait)
        _last_message_at = time.monotonic()
        response = await client.post("/api/chat/messages", json={"content": content})
        assert response.status_code == 200, response.text
        reply, errors = [], []
        for block in response.text.strip().split("\n\n"):
            lines = dict(line.split(": ", 1) for line in block.splitlines())
            data = json.loads(lines["data"])
            if lines["event"] == "delta":
                reply.append(data["text"])
            elif lines["event"] == "error":
                errors.append(data["message"])
        print(f"\n>>> {content}\n<<< {''.join(reply)}")
        assert not errors, errors
        return "".join(reply)

    return send


@pytest.fixture
def items():
    async def get(client) -> dict[str, dict]:
        body = (await client.get("/api/list")).json()
        return {i["name"].lower(): i for g in body["groups"] for i in g["items"]}

    return get

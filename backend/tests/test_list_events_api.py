"""Strumień SSE `GET /api/list/events` przez prawdziwy serwer HTTP.

ASGITransport z httpx buforuje całą odpowiedź, więc nieskończonego strumienia nie da się nim
czytać — te testy uruchamiają uvicorn na wolnym porcie w tej samej pętli zdarzeń.
"""

import asyncio
import json
from collections.abc import AsyncIterator

import httpx
import pytest
import uvicorn
from sqlalchemy import select

from kupto.chat.llm import TextDelta, ToolCall
from kupto.lists.events import BrokerUnavailable
from kupto.models import User

PASSWORD = "haslo-testowe"


@pytest.fixture
async def server_url(app) -> AsyncIterator[str]:
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=0,
        lifespan="off",
        log_level="warning",
        timeout_graceful_shutdown=1,
    )
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    while not server.started:  # noqa: ASYNC110 — uvicorn nie wystawia zdarzenia startu
        await asyncio.sleep(0.01)
    port = server.servers[0].sockets[0].getsockname()[1]
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    await task


@pytest.fixture
async def live_client(server_url):
    """Klient HTTP zalogowany na prawdziwym serwerze (użytkownik musi już istnieć)."""
    clients: list[httpx.AsyncClient] = []

    async def factory(login: str) -> httpx.AsyncClient:
        client = httpx.AsyncClient(base_url=server_url, timeout=10)
        clients.append(client)
        response = await client.post("/api/auth/login", json={"login": login, "password": PASSWORD})
        assert response.status_code == 200, response.text
        return client

    yield factory
    for client in clients:
        await client.aclose()


class EventStream:
    """Zdarzenia SSE czytane w tle: nazwa zdarzenia, „ping” dla komentarza, None po końcu."""

    def __init__(self, response: httpx.Response):
        self.response = response
        self._events: asyncio.Queue[str | None] = asyncio.Queue()
        self._reader = asyncio.create_task(self._read())

    async def _read(self) -> None:
        block: list[str] = []
        try:
            async for line in self.response.aiter_lines():
                if line:
                    block.append(line)
                    continue
                names = [b[6:].strip() for b in block if b.startswith("event:")]
                if names:
                    self._events.put_nowait(names[0])
                elif any(b.startswith(":") for b in block):
                    self._events.put_nowait("ping")
                block = []  # np. sam `retry:`
        except httpx.HTTPError:
            pass
        self._events.put_nowait(None)

    async def next(self, within: float = 5) -> str | None:
        async with asyncio.timeout(within):
            return await self._events.get()

    async def expect_quiet(self, seconds: float = 0.3) -> None:
        with pytest.raises(TimeoutError):
            await self.next(within=seconds)

    async def close(self) -> None:
        self._reader.cancel()
        await self.response.aclose()


@pytest.fixture
async def open_stream():
    streams: list[EventStream] = []

    async def factory(client: httpx.AsyncClient) -> EventStream:
        request = client.build_request("GET", "/api/list/events")
        response = await client.send(request, stream=True)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert response.headers["cache-control"] == "no-cache"
        stream = EventStream(response)
        streams.append(stream)
        assert await stream.next() == "ready"
        return stream

    yield factory
    for stream in streams:
        await stream.close()


async def test_stream_signals_changes_of_own_household_only(
    household_with, live_client, open_stream
):
    ala, _ = await household_with("ala", "ola")
    (ewa,) = await household_with("ewa", name="Sąsiedzi")
    ola_stream = await open_stream(await live_client("ola"))
    ewa_stream = await open_stream(await live_client("ewa"))

    await ala.post("/api/list/needs", json={"name": "mleko"})

    assert await ola_stream.next() == "list_changed"
    await ewa_stream.expect_quiet()


async def test_stream_sends_heartbeat(settings, household_with, live_client, open_stream):
    settings.list_events_heartbeat_seconds = 0.2
    await household_with("ala")
    stream = await open_stream(await live_client("ala"))

    assert await stream.next(within=2) == "ping"
    assert await stream.next(within=2) == "ping"


async def test_chat_change_reaches_other_members_stream(
    household_with, live_client, open_stream, fake_llm
):
    ala, _ = await household_with("ala", "ola")
    stream = await open_stream(await live_client("ola"))
    need = {"name": "mleko", "amount": None, "unit": None, "note": None, "category": "Nabiał"}
    fake_llm.rounds += [
        [ToolCall("call_1", "add_needs", json.dumps({"items": [need]}))],
        [TextDelta("Gotowe.")],
    ]

    response = await ala.post("/api/chat/messages", json={"content": "Dodaj mleko"})

    assert response.status_code == 200
    assert await stream.next() == "list_changed"


async def test_stream_ends_when_member_is_removed(
    session, household_with, live_client, open_stream
):
    ala, _ = await household_with("ala", "ola")
    stream = await open_stream(await live_client("ola"))
    ola_id = await session.scalar(select(User.id).where(User.login == "ola"))

    assert (await ala.delete(f"/api/households/me/members/{ola_id}")).status_code == 200

    assert await stream.next() is None


async def test_stream_requires_session_and_household(client, login_as):
    assert (await client.get("/api/list/events")).status_code == 401

    ala = await login_as("ala")
    response = await ala.get("/api/list/events")

    assert response.status_code == 409
    assert response.json()["code"] == "no_household"


async def test_stream_releases_db_connection_and_cleans_up_on_disconnect(
    app, household_with, live_client, open_stream
):
    await household_with("ala")
    client = await live_client("ala")
    pool = app.state.sessionmaker.kw["bind"].pool
    broker = app.state.list_events

    streams = [await open_stream(client) for _ in range(3)]

    assert broker.subscription_count == 3
    assert pool.checkedout() == 0  # strumienie nie trzymają połączeń z puli

    for stream in streams:
        await stream.close()
    async with asyncio.timeout(5):
        while broker.subscription_count:  # noqa: ASYNC110 — stan brokera bez zdarzenia
            await asyncio.sleep(0.05)


async def test_stream_unavailable_without_listen_connection(app, household_with, live_client):
    await household_with("ala")
    client = await live_client("ala")

    async def unavailable(seconds: float) -> None:
        raise BrokerUnavailable

    app.state.list_events.wait_ready = unavailable

    assert (await client.get("/api/list/events")).status_code == 503

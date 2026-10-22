"""Transport produkcyjny (pywebpush) wobec lokalnej atrapy usługi push — bez internetu."""

import asyncio
import os

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from py_vapid import Vapid

from kupto.config import Settings
from kupto.push.keys import b64url, generate
from kupto.push.notifier import Target, WebPushTransport
from kupto.push.vapid import VapidConfig

PUBLIC, PRIVATE = generate()


@pytest.fixture
async def push_service():
    """Odpowiada kodem z `/<kod>`; `/slow` nie odpowiada przez 5 s. Zapisuje żądania."""
    received: list[web.Request] = []
    bodies: list[bytes] = []

    async def handler(request: web.Request) -> web.Response:
        received.append(request)
        bodies.append(await request.read())
        if request.path == "/slow":
            await asyncio.sleep(5)
        return web.Response(status=int(request.path.strip("/") or 201))

    app = web.Application()
    app.router.add_route("POST", "/{tail:.*}", handler)
    server = TestServer(app)
    await server.start_server()
    yield server, received, bodies
    await server.close()


@pytest.fixture
async def transport():
    config = VapidConfig.from_settings(
        Settings(
            jwt_secret="x" * 32,
            vapid_public_key=PUBLIC,
            vapid_private_key=PRIVATE,
            vapid_subject="mailto:kupto@example.com",
        )
    )
    transport = WebPushTransport(config, timeout_seconds=0.5)
    yield transport
    await transport.aclose()


def target(url: str) -> Target:
    p256dh = ec.generate_private_key(ec.SECP256R1()).public_key()
    return Target(
        subscription_id=1,
        endpoint=url,
        p256dh=b64url(p256dh.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)),
        auth=b64url(os.urandom(16)),
    )


async def test_sends_encrypted_payload_with_vapid_and_headers(push_service, transport):
    server, received, bodies = push_service

    status = await transport.send(
        target(str(server.make_url("/201"))),
        '{"title": "Zakupy"}',
        ttl=600,
        urgency="high",
        topic="shopping",
    )

    assert status == 201
    (request,) = received
    assert request.headers["TTL"] == "600"
    assert request.headers["Urgency"] == "high"
    assert request.headers["Topic"] == "shopping"
    assert request.headers["Content-Encoding"] == "aes128gcm"
    assert b"Zakupy" not in bodies[0]  # treść zaszyfrowana
    scheme, token = request.headers["Authorization"].split(" ", 1)
    assert scheme == "vapid"
    params = dict(p.strip().split("=", 1) for p in token.split(","))
    assert params["k"] == PUBLIC
    assert Vapid.verify(request.headers["Authorization"])


@pytest.mark.parametrize("code", [404, 410, 500])
async def test_returns_error_status(push_service, transport, code):
    server, _, _ = push_service

    status = await transport.send(
        target(str(server.make_url(f"/{code}"))), "{}", ttl=60, urgency="normal", topic=None
    )

    assert status == code


async def test_times_out(push_service, transport):
    server, _, _ = push_service

    with pytest.raises(TimeoutError):
        await transport.send(
            target(str(server.make_url("/slow"))), "{}", ttl=60, urgency="normal", topic=None
        )

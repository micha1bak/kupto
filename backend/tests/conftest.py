import asyncio
import re
from collections.abc import AsyncIterator, Callable
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from testcontainers.community.postgres import PostgresContainer

from kupto.chat.llm import FakeLLMClient, LLMClient
from kupto.config import Settings
from kupto.db import Base
from kupto.mail import EmailMessage
from kupto.main import create_app
from kupto.models import PurchasedItem, ShoppingTrip
from kupto.push.notifier import PushTransport

BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def database_url() -> AsyncIterator[str]:
    with PostgresContainer("postgres:18.1", driver="asyncpg") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture(scope="session")
async def migrated_database(database_url: str) -> str:
    config = Config(BACKEND_DIR / "alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    config.attributes["configure_logger"] = False
    await asyncio.to_thread(command.upgrade, config, "head")
    return database_url


@pytest.fixture
def settings(migrated_database: str) -> Settings:
    return Settings(
        database_url=migrated_database,
        jwt_secret="test-secret-that-is-long-enough-for-hs256",
        cookie_secure=False,
        openai_api_key="",
    )


@pytest.fixture
def fake_llm() -> FakeLLMClient:
    """Model testowy — testy dopisują rundy do `fake_llm.rounds`."""
    return FakeLLMClient(rounds=[])


@pytest.fixture
def llm_client(fake_llm: FakeLLMClient) -> LLMClient:
    """Model używany przez aplikację; ewaluacje podmieniają go na prawdziwy klient OpenAI."""
    return fake_llm


@pytest.fixture
def push_transport() -> PushTransport | None:
    """Transport powiadomień push; testy powiadomień podmieniają go na atrapę."""
    return None


class FakeMailSender:
    """Atrapa wysyłki maili: zapamiętuje wiadomości. `delivers` = czy wysyłka „działa”."""

    def __init__(self, delivers: bool):
        self.delivers = delivers
        self.sent: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> None:
        self.sent.append(message)

    def last_token(self, to: str | None = None) -> str:
        """Token z linku w ostatnim mailu (opcjonalnie do danego adresata)."""
        messages = [m for m in self.sent if to is None or m.to == to]
        assert messages, "brak maili"
        return re.search(r"#token=([\w-]+)", messages[-1].body).group(1)


@pytest.fixture
def mail_delivers() -> bool:
    """Domyślnie wysyłka niedostępna (jak produkcja przed SES) — nikt nie jest blokowany.
    Testy weryfikacji adresów nadpisują ten fixture na `True`."""
    return False


@pytest.fixture
def mail(mail_delivers: bool) -> FakeMailSender:
    return FakeMailSender(delivers=mail_delivers)


@pytest.fixture
async def app(
    settings: Settings,
    llm_client: LLMClient,
    push_transport: PushTransport | None,
    mail: FakeMailSender,
) -> AsyncIterator[FastAPI]:
    app = create_app(
        settings, llm_client=llm_client, push_transport=push_transport, mail_sender=mail
    )
    yield app
    # ASGITransport nie uruchamia lifespan.
    await app.state.list_events.close()
    await app.state.notifier.aclose()
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    async with app.state.sessionmaker() as session:
        await session.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
        await session.commit()
    await app.state.sessionmaker.kw["bind"].dispose()


@pytest.fixture
async def session(app: FastAPI) -> AsyncIterator[AsyncSession]:
    async with app.state.sessionmaker() as session:
        yield session


@pytest.fixture
async def make_client(app: FastAPI) -> AsyncIterator[Callable[..., AsyncClient]]:
    """Tworzy osobnych klientów HTTP — każdy z własnym słoikiem ciasteczek (osobny użytkownik)."""
    clients: list[AsyncClient] = []

    def factory(ip: str | None = None) -> AsyncClient:
        # Każdy klient z własnego adresu IP (osobne urządzenie) — limity prób na IP (#77)
        # nie łączą użytkowników jednego testu; `ip` wymusza wspólny adres.
        address = ip or f"10.0.{len(clients) // 250}.{len(clients) % 250 + 1}"
        transport = ASGITransport(app=app, client=(address, 123))
        client = AsyncClient(transport=transport, base_url="http://test")
        clients.append(client)
        return client

    yield factory
    for client in clients:
        await client.aclose()


@pytest.fixture
def client(make_client: Callable[[], AsyncClient]) -> AsyncClient:
    return make_client()


@pytest.fixture
def login_as(make_client: Callable[[], AsyncClient]):
    """Fabryka użytkowników: rejestruje (jeśli trzeba) i loguje, zwraca zalogowanego klienta.

    Konto „ala” ma adres ala@example.com i (domyślnie) imię „ala” — asercje na imionach
    domowników zostają krótkie.
    """

    async def factory(
        login: str, password: str = "haslo-testowe", name: str | None = None
    ) -> AsyncClient:
        client = make_client()
        email = f"{login}@example.com"
        payload = {"email": email, "password": password, "name": name or login}
        await client.post("/api/auth/register", json=payload)
        response = await client.post("/api/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200, response.text
        return client

    return factory


@pytest.fixture
def household_with(login_as):
    """Fabryka gospodarstw: pierwszy login to właściciel, kolejni to członkowie."""

    async def factory(*logins: str, name: str = "Dom") -> list[AsyncClient]:
        clients = [await login_as(login) for login in logins]
        response = await clients[0].post("/api/households", json={"name": name})
        assert response.status_code == 201, response.text
        for login in logins[1:]:
            response = await clients[0].post(
                "/api/households/me/members", json={"email": f"{login}@example.com"}
            )
            assert response.status_code == 201, response.text
        return clients

    return factory


@pytest.fixture
def purchase_history(app: FastAPI):
    """Odczyt historii zakupów (zakończenia z pozycjami i zapotrzebowaniami) w osobnej sesji."""

    async def load(household_id: int | None = None) -> list[ShoppingTrip]:
        statement = (
            select(ShoppingTrip)
            .options(selectinload(ShoppingTrip.items).selectinload(PurchasedItem.needs))
            .order_by(ShoppingTrip.id)
        )
        if household_id is not None:
            statement = statement.where(ShoppingTrip.household_id == household_id)
        async with app.state.sessionmaker() as session:
            return list(await session.scalars(statement))

    return load

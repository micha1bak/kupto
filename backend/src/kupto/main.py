from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from kupto.auth.router import router as auth_router
from kupto.chat.llm import LLMClient
from kupto.chat.router import router as chat_router
from kupto.config import Settings, get_settings
from kupto.db import create_sessionmaker
from kupto.errors import register_error_handlers
from kupto.households.router import router as households_router
from kupto.lists.events import ListEventBroker
from kupto.lists.router import router as list_router
from kupto.logs import configure_logging


def create_app(settings: Settings | None = None, llm_client: LLMClient | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        await app.state.list_events.close()

    app = FastAPI(
        title="Kupto",
        version="2.0.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.sessionmaker = create_sessionmaker(settings.database_url)
    # Nasłuch LISTEN startuje leniwie przy pierwszym strumieniu zmian listy.
    app.state.list_events = ListEventBroker(settings.database_url)
    app.state.llm_client = llm_client  # None: klient OpenAI tworzony przy pierwszym użyciu
    register_error_handlers(app)
    app.include_router(auth_router)
    app.include_router(households_router)
    app.include_router(list_router)
    app.include_router(chat_router)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app

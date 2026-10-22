from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # hide_input_in_errors: błąd walidacji przy starcie nie może wypisać sekretów do logów.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    database_url: str = "postgresql+asyncpg://kupto:kupto@localhost:5432/kupto"
    # Wymagany i długi: pusty sekret wywracałby logowanie (500), słaby ułatwiałby fałszowanie sesji.
    jwt_secret: str = Field(min_length=32)
    jwt_ttl_days: int = 30
    cookie_secure: bool = True

    openai_api_key: str = ""
    # Dowolny dostawca zgodny z OpenAI Responses API, np. https://api.groq.com/openai/v1
    openai_base_url: str = ""
    openai_model: str = "gpt-4.1-mini"
    openai_timeout_seconds: float = 60.0

    chat_rate_limit_per_hour: int = 30
    chat_history_limit: int = 20
    chat_max_tool_rounds: int = 5

    # Podtrzymanie strumienia zmian listy (SSE) — poniżej limitów bezczynności proxy (nginx 300 s).
    list_events_heartbeat_seconds: float = Field(default=20.0, gt=0, le=30)


@lru_cache
def get_settings() -> Settings:
    return Settings()

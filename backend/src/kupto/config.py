from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://kupto:kupto@localhost:5432/kupto"
    jwt_secret: str = "dev-secret-change-me"
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


@lru_cache
def get_settings() -> Settings:
    return Settings()

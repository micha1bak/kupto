import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

BACKEND_DIR = Path(__file__).resolve().parents[1]


async def table_exists(database_url: str, name: str) -> bool:
    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        exists = await connection.scalar(
            text("SELECT to_regclass(:name) IS NOT NULL"), {"name": name}
        )
    await engine.dispose()
    return exists


async def test_category_pins_migration_downgrades_and_upgrades(migrated_database):
    config = Config(BACKEND_DIR / "alembic.ini")
    config.set_main_option("sqlalchemy.url", migrated_database)
    config.attributes["configure_logger"] = False

    await asyncio.to_thread(command.downgrade, config, "0001")
    assert not await table_exists(migrated_database, "user_category_pins")

    await asyncio.to_thread(command.upgrade, config, "head")
    assert await table_exists(migrated_database, "user_category_pins")

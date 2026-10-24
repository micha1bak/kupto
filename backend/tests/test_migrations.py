import asyncio
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import make_url, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

BACKEND_DIR = Path(__file__).resolve().parents[1]

# Tabele sprzed historii zakupów (stan po migracji 0002).
EXISTING_TABLES = (
    "users",
    "households",
    "shopping_lists",
    "household_products",
    "list_items",
    "needs",
    "user_category_pins",
    "chat_messages",
    "chat_pending_actions",
)
HISTORY_TABLES = ("shopping_trips", "purchased_items", "purchased_needs")


# Dane jak na produkcji przed wdrożeniem: gospodarstwo z dwoma członkami, lista z kupioną
# i niekupioną pozycją, zapotrzebowania, pamięć kategorii, przypięcia i historia czatu.
SEED_STATEMENTS = (
    "INSERT INTO users (id, login, password_hash, created_at) VALUES "
    "(1, 'ala', 'x', now()), (2, 'ola', 'x', now())",
    "INSERT INTO households (id, name, owner_id, created_at) VALUES (1, 'Dom', 1, now())",
    "UPDATE users SET household_id = 1, joined_household_at = now()",
    "INSERT INTO shopping_lists (id, household_id) VALUES (1, 1)",
    "INSERT INTO household_products VALUES (1, 'mleko', 'Nabiał')",
    "INSERT INTO list_items (id, list_id, name, normalized_name, category, bought_at, "
    "bought_by_id, created_at) VALUES "
    "(1, 1, 'mleko', 'mleko', 'Nabiał', now(), 2, now()), "
    "(2, 1, 'chleb', 'chleb', 'Pieczywo', NULL, NULL, now())",
    "INSERT INTO needs (id, item_id, user_id, amount, unit, note, created_at) VALUES "
    "(1, 1, 1, 2, 'l', 'bez laktozy', now()), (2, 2, 2, NULL, NULL, NULL, now())",
    "INSERT INTO user_category_pins VALUES (1, 'Chemia i higiena', 0)",
    "INSERT INTO chat_messages (user_id, household_id, role, content, created_at) "
    "VALUES (1, 1, 'user', 'kup mleko', now())",
    "INSERT INTO chat_pending_actions VALUES (1, 'finish_shopping', now())",
)


def alembic_config(database_url: str) -> Config:
    config = Config(BACKEND_DIR / "alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    config.attributes["configure_logger"] = False
    return config


async def migrate(database_url: str, direction: str, revision: str) -> None:
    action = command.upgrade if direction == "up" else command.downgrade
    await asyncio.to_thread(action, alembic_config(database_url), revision)


async def execute(database_url: str, *statements: str) -> None:
    engine = create_async_engine(database_url)
    async with engine.begin() as connection:
        for statement in statements:
            await connection.execute(text(statement))
    await engine.dispose()


async def table_exists(database_url: str, name: str) -> bool:
    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        exists = await connection.scalar(
            text("SELECT to_regclass(:name) IS NOT NULL"), {"name": name}
        )
    await engine.dispose()
    return exists


async def snapshot(database_url: str, tables: tuple[str, ...]) -> dict[str, list[tuple]]:
    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        rows = {
            table: [
                tuple(row)
                for row in await connection.execute(text(f"SELECT * FROM {table} ORDER BY 1, 2"))
            ]
            for table in tables
        }
    await engine.dispose()
    return rows


@pytest.fixture
async def empty_database(database_url: str) -> AsyncIterator[str]:
    """Osobna, pusta baza w kontenerze testowym — migracje nie ruszają bazy innych testów."""
    name = f"migrations_{uuid.uuid4().hex[:12]}"
    admin = create_async_engine(database_url, isolation_level="AUTOCOMMIT")
    async with admin.connect() as connection:
        await connection.execute(text(f'CREATE DATABASE "{name}"'))
    yield make_url(database_url).set(database=name).render_as_string(hide_password=False)
    async with admin.connect() as connection:
        await connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
    await admin.dispose()


async def test_category_pins_migration_downgrades_and_upgrades(migrated_database):
    await migrate(migrated_database, "down", "0001")
    assert not await table_exists(migrated_database, "user_category_pins")
    assert not await table_exists(migrated_database, "shopping_trips")

    await migrate(migrated_database, "up", "head")
    assert await table_exists(migrated_database, "user_category_pins")
    assert await table_exists(migrated_database, "shopping_trips")


async def test_purchase_history_migration_keeps_existing_data(empty_database):
    await migrate(empty_database, "up", "0002")
    await execute(empty_database, *SEED_STATEMENTS)
    before = await snapshot(empty_database, EXISTING_TABLES)

    await migrate(empty_database, "up", "0003")

    assert await snapshot(empty_database, EXISTING_TABLES) == before
    assert await snapshot(empty_database, HISTORY_TABLES) == {t: [] for t in HISTORY_TABLES}
    # Nowe tabele przyjmują historię odwołującą się do istniejących danych i typów enum.
    await execute(
        empty_database,
        "INSERT INTO shopping_trips (id, household_id, finished_at, finished_by_id) "
        "VALUES (1, 1, now(), 1)",
        "INSERT INTO purchased_items (id, trip_id, name, normalized_name, category, bought_at, "
        "bought_by_id) VALUES (1, 1, 'mleko', 'mleko', 'Nabiał', now(), 2)",
        "INSERT INTO purchased_needs (purchased_item_id, user_id, amount, unit, note, "
        "requested_at) VALUES (1, 1, 2, 'l', 'bez laktozy', now())",
    )

    await migrate(empty_database, "down", "0002")

    for table in HISTORY_TABLES:
        assert not await table_exists(empty_database, table)
    assert await snapshot(empty_database, EXISTING_TABLES) == before

    await migrate(empty_database, "up", "0003")
    assert await snapshot(empty_database, HISTORY_TABLES) == {t: [] for t in HISTORY_TABLES}


async def column_exists(database_url: str, table: str, column: str) -> bool:
    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        exists = await connection.scalar(
            text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
                "WHERE table_name = :table AND column_name = :column)"
            ),
            {"table": table, "column": column},
        )
    await engine.dispose()
    return exists


async def test_shopping_status_migration_keeps_existing_data(empty_database):
    await migrate(empty_database, "up", "0003")
    await execute(
        empty_database,
        *SEED_STATEMENTS,
        "INSERT INTO shopping_trips (id, household_id, finished_at, finished_by_id) "
        "VALUES (1, 1, now(), 1)",
    )
    tables = (*EXISTING_TABLES, *HISTORY_TABLES)
    before = await snapshot(empty_database, tables)

    await migrate(empty_database, "up", "0004")

    # Istniejące wiersze bez zmian (porównujemy kolumny sprzed migracji), status pusty.
    after = await snapshot(empty_database, tables)
    assert [row[:-1] for row in after["users"]] == before["users"]
    assert [row[-1] for row in after["users"]] == [None, None]
    assert {t: rows for t, rows in after.items() if t != "users"} == {
        t: rows for t, rows in before.items() if t != "users"
    }
    await execute(empty_database, "UPDATE users SET shopping_since = now() WHERE id = 1")

    await migrate(empty_database, "down", "0003")

    assert not await column_exists(empty_database, "users", "shopping_since")
    assert await snapshot(empty_database, tables) == before

    await migrate(empty_database, "up", "head")
    assert await column_exists(empty_database, "users", "shopping_since")


async def test_push_subscriptions_migration_keeps_existing_data(empty_database):
    await migrate(empty_database, "up", "0004")
    await execute(empty_database, *SEED_STATEMENTS)
    tables = (*EXISTING_TABLES, *HISTORY_TABLES)
    before = await snapshot(empty_database, tables)

    await migrate(empty_database, "up", "0005")

    assert await snapshot(empty_database, tables) == before
    assert await snapshot(empty_database, ("push_subscriptions",)) == {"push_subscriptions": []}
    # Kilka urządzeń jednego użytkownika, endpoint unikalny.
    insert = (
        "INSERT INTO push_subscriptions (user_id, endpoint, p256dh, auth, created_at, "
        "updated_at) VALUES "
    )
    await execute(
        empty_database,
        insert + "(1, 'https://fcm.googleapis.com/a', 'k', 'a', now(), now()), "
        "(1, 'https://fcm.googleapis.com/b', 'k', 'a', now(), now())",
    )
    with pytest.raises(IntegrityError):
        await execute(
            empty_database, insert + "(2, 'https://fcm.googleapis.com/a', 'k', 'a', now(), now())"
        )

    await migrate(empty_database, "down", "0004")

    assert not await table_exists(empty_database, "push_subscriptions")
    assert await snapshot(empty_database, tables) == before

    await migrate(empty_database, "up", "head")
    assert await table_exists(empty_database, "push_subscriptions")


async def test_product_pins_migration_keeps_existing_data(empty_database):
    await migrate(empty_database, "up", "0005")
    await execute(
        empty_database,
        *SEED_STATEMENTS,
        "INSERT INTO push_subscriptions (user_id, endpoint, p256dh, auth, created_at, "
        "updated_at) VALUES (1, 'https://fcm.googleapis.com/a', 'k', 'a', now(), now())",
    )
    tables = (*EXISTING_TABLES, *HISTORY_TABLES, "push_subscriptions")
    before = await snapshot(empty_database, tables)

    await migrate(empty_database, "up", "0006")

    assert await snapshot(empty_database, tables) == before
    assert await snapshot(empty_database, ("user_product_pins",)) == {"user_product_pins": []}
    # Przypięcia w obrębie kategorii: ranga unikalna w kategorii, ten sam produkt raz.
    insert = (
        "INSERT INTO user_product_pins (user_id, normalized_name, category, after_name, "
        "at_end, position) VALUES "
    )
    await execute(
        empty_database,
        insert
        + "(1, 'ser', 'Nabiał', NULL, false, 0), (1, 'jogurt', 'Nabiał', 'mleko', false, 1), "
        "(1, 'chleb', 'Pieczywo', NULL, true, 0), (2, 'ser', 'Nabiał', NULL, false, 0)",
    )
    with pytest.raises(IntegrityError):
        await execute(empty_database, insert + "(1, 'kefir', 'Nabiał', NULL, false, 1)")
    with pytest.raises(IntegrityError):
        await execute(empty_database, insert + "(1, 'ser', 'Inne', NULL, false, 0)")

    await migrate(empty_database, "down", "0005")

    assert not await table_exists(empty_database, "user_product_pins")
    assert await snapshot(empty_database, tables) == before

    await migrate(empty_database, "up", "head")
    assert await table_exists(empty_database, "user_product_pins")


async def test_notification_preferences_migration_keeps_existing_data(empty_database):
    await migrate(empty_database, "up", "0006")
    await execute(
        empty_database,
        *SEED_STATEMENTS,
        "INSERT INTO push_subscriptions (user_id, endpoint, p256dh, auth, created_at, "
        "updated_at) VALUES (1, 'https://fcm.googleapis.com/a', 'k', 'a', now(), now())",
        "INSERT INTO user_product_pins (user_id, normalized_name, category, after_name, "
        "at_end, position) VALUES (1, 'ser', 'Nabiał', NULL, false, 0)",
    )
    tables = (*EXISTING_TABLES, *HISTORY_TABLES, "push_subscriptions", "user_product_pins")
    before = await snapshot(empty_database, tables)

    await migrate(empty_database, "up", "0007")

    assert await snapshot(empty_database, tables) == before
    assert await snapshot(empty_database, ("notification_preferences",)) == {
        "notification_preferences": []
    }
    # Typ to tekst bez enuma bazy (nowy typ, np. #40, bez migracji); jeden wybór na typ.
    insert = "INSERT INTO notification_preferences (user_id, type, enabled, updated_at) VALUES "
    await execute(
        empty_database,
        insert + "(1, 'shopping_started', false, now()), (1, 'usual_reminder', true, now()), "
        "(2, 'shopping_started', true, now())",
    )
    with pytest.raises(IntegrityError):
        await execute(empty_database, insert + "(1, 'shopping_started', true, now())")
    with pytest.raises(IntegrityError):
        await execute(empty_database, insert + "(99, 'items_added', true, now())")

    await migrate(empty_database, "down", "0006")

    assert not await table_exists(empty_database, "notification_preferences")
    assert await snapshot(empty_database, tables) == before

    await migrate(empty_database, "up", "head")
    assert await table_exists(empty_database, "notification_preferences")


async def test_usual_reminders_migration_keeps_existing_data(empty_database):
    await migrate(empty_database, "up", "0007")
    await execute(
        empty_database,
        *SEED_STATEMENTS,
        "INSERT INTO notification_preferences (user_id, type, enabled, updated_at) VALUES "
        "(1, 'usual_reminder', true, now())",
    )
    tables = (*EXISTING_TABLES, *HISTORY_TABLES, "notification_preferences")
    before = await snapshot(empty_database, tables)

    await migrate(empty_database, "up", "0008")

    assert await snapshot(empty_database, tables) == before
    assert await snapshot(empty_database, ("usual_reminders",)) == {"usual_reminders": []}
    # Jeden wpis na produkt gospodarstwa, tylko dla istniejących gospodarstw.
    insert = "INSERT INTO usual_reminders (household_id, normalized_name, reminded_at) VALUES "
    await execute(empty_database, insert + "(1, 'mleko', now()), (1, 'chleb', now())")
    with pytest.raises(IntegrityError):
        await execute(empty_database, insert + "(1, 'mleko', now())")
    with pytest.raises(IntegrityError):
        await execute(empty_database, insert + "(99, 'mleko', now())")

    await migrate(empty_database, "down", "0007")

    assert not await table_exists(empty_database, "usual_reminders")
    assert await snapshot(empty_database, tables) == before

    await migrate(empty_database, "up", "head")
    assert await table_exists(empty_database, "usual_reminders")


RECIPE_TABLES = ("recipes", "recipe_ingredients")


async def test_household_recipes_migration_keeps_existing_data(empty_database):
    await migrate(empty_database, "up", "0008")
    await execute(
        empty_database,
        *SEED_STATEMENTS,
        "INSERT INTO usual_reminders (household_id, normalized_name, reminded_at) VALUES "
        "(1, 'mleko', now())",
    )
    tables = (*EXISTING_TABLES, *HISTORY_TABLES, "usual_reminders")
    before = await snapshot(empty_database, tables)

    await migrate(empty_database, "up", "0009")

    assert await snapshot(empty_database, tables) == before
    assert await snapshot(empty_database, RECIPE_TABLES) == {t: [] for t in RECIPE_TABLES}
    # Przepis gospodarstwa ze składnikami (istniejące typy enum), nazwa unikalna w gospodarstwie.
    insert = (
        "INSERT INTO recipes (id, household_id, name, normalized_name, created_by_id, "
        "created_at, updated_at) VALUES "
    )
    await execute(
        empty_database,
        insert + "(1, 1, 'Naleśniki', 'naleśniki', 1, now(), now())",
        "INSERT INTO recipe_ingredients (recipe_id, position, name, amount, unit, note, "
        "category) VALUES (1, 0, 'mleko', 0.5, 'l', NULL, 'Nabiał'), "
        "(1, 1, 'mąka', NULL, NULL, '2 szklanki', NULL)",
    )
    with pytest.raises(IntegrityError):
        await execute(empty_database, insert + "(2, 1, 'naleśniki', 'naleśniki', 1, now(), now())")
    with pytest.raises(IntegrityError):
        await execute(empty_database, insert + "(3, 99, 'bigos', 'bigos', 1, now(), now())")
    # Usunięcie przepisu usuwa jego składniki.
    await execute(empty_database, "DELETE FROM recipes WHERE id = 1")
    assert await snapshot(empty_database, ("recipe_ingredients",)) == {"recipe_ingredients": []}
    await execute(empty_database, insert + "(1, 1, 'Naleśniki', 'naleśniki', 1, now(), now())")

    await migrate(empty_database, "down", "0008")

    for table in RECIPE_TABLES:
        assert not await table_exists(empty_database, table)
    assert await snapshot(empty_database, tables) == before

    await migrate(empty_database, "up", "head")
    assert await snapshot(empty_database, RECIPE_TABLES) == {t: [] for t in RECIPE_TABLES}


async def test_household_preferences_migration_keeps_existing_data(empty_database):
    await migrate(empty_database, "up", "0009")
    await execute(
        empty_database,
        *SEED_STATEMENTS,
        "INSERT INTO recipes (id, household_id, name, normalized_name, created_by_id, "
        "created_at, updated_at) VALUES (1, 1, 'Naleśniki', 'naleśniki', 1, now(), now())",
    )
    tables = (*EXISTING_TABLES, *HISTORY_TABLES, *RECIPE_TABLES)
    before = await snapshot(empty_database, tables)

    await migrate(empty_database, "up", "0010")

    assert await snapshot(empty_database, tables) == before
    preferences = ("household_preferences",)
    assert await snapshot(empty_database, preferences) == {"household_preferences": []}
    # Jeden wiersz na gospodarstwo, listy domyślnie puste.
    insert = "INSERT INTO household_preferences (household_id, people, updated_at) VALUES "
    await execute(empty_database, insert + "(1, 4, now())")
    (row,) = (await snapshot(empty_database, preferences))["household_preferences"]
    assert row[:5] == (1, 4, [], [], [])
    with pytest.raises(IntegrityError):
        await execute(empty_database, insert + "(1, 2, now())")
    with pytest.raises(IntegrityError):
        await execute(empty_database, insert + "(99, 2, now())")
    # Usunięcie gospodarstwa usuwa jego preferencje.
    await execute(
        empty_database,
        "INSERT INTO households (id, name, owner_id, created_at) VALUES (2, 'Inny', 1, now())",
        insert + "(2, 1, now())",
        "DELETE FROM households WHERE id = 2",
    )
    assert len((await snapshot(empty_database, preferences))["household_preferences"]) == 1

    await migrate(empty_database, "down", "0009")

    assert not await table_exists(empty_database, "household_preferences")
    assert await snapshot(empty_database, tables) == before

    await migrate(empty_database, "up", "head")
    assert await snapshot(empty_database, preferences) == {"household_preferences": []}


async def test_meal_plan_migration_keeps_existing_data(empty_database):
    await migrate(empty_database, "up", "0010")
    recipe = (
        "INSERT INTO recipes (id, household_id, name, normalized_name, created_by_id, "
        "created_at, updated_at) VALUES "
    )
    await execute(
        empty_database,
        *SEED_STATEMENTS,
        recipe + "(1, 1, 'Naleśniki', 'naleśniki', 1, now(), now())",
        "INSERT INTO household_preferences (household_id, people, updated_at) VALUES (1, 4, now())",
    )
    tables = (*EXISTING_TABLES, *HISTORY_TABLES, *RECIPE_TABLES, "household_preferences")
    before = await snapshot(empty_database, tables)

    await migrate(empty_database, "up", "0011")

    assert await snapshot(empty_database, tables) == before
    plan = ("meal_plan_entries",)
    assert await snapshot(empty_database, plan) == {"meal_plan_entries": []}
    insert = (
        "INSERT INTO meal_plan_entries (household_id, day, name, recipe_id, planned_by_id, "
        "created_at, updated_at) VALUES "
    )
    await execute(
        empty_database,
        recipe + "(2, 1, 'Bigos', 'bigos', 1, now(), now())",
        insert + "(1, '2026-10-26', 'Naleśniki', 1, 1, now(), now())",
        insert + "(1, '2026-10-27', 'Bigos', 2, 2, now(), now())",
    )
    # Jeden obiad na dzień w gospodarstwie; gospodarstwo i przepis muszą istnieć.
    for values in (
        "(1, '2026-10-26', 'Pierogi', NULL, 1, now(), now())",
        "(99, '2026-10-28', 'Pierogi', NULL, 1, now(), now())",
        "(1, '2026-10-28', 'Pierogi', 99, 1, now(), now())",
    ):
        with pytest.raises(IntegrityError):
            await execute(empty_database, insert + values)
    # Usunięcie przepisu zostawia danie w planie bez odwołania do przepisu.
    await execute(empty_database, "DELETE FROM recipes WHERE id = 2")
    rows = (await snapshot(empty_database, plan))["meal_plan_entries"]
    assert [(r[2].isoformat(), r[3], r[4]) for r in rows] == [
        ("2026-10-26", "Naleśniki", 1),
        ("2026-10-27", "Bigos", None),
    ]

    await migrate(empty_database, "down", "0010")

    assert not await table_exists(empty_database, "meal_plan_entries")
    assert await snapshot(empty_database, tables) == before

    await migrate(empty_database, "up", "head")
    assert await snapshot(empty_database, plan) == {"meal_plan_entries": []}


async def test_group_chat_migration_archives_private_history(empty_database):
    await migrate(empty_database, "up", "0011")
    await execute(
        empty_database,
        *SEED_STATEMENTS,
        "INSERT INTO chat_messages (user_id, household_id, role, content, created_at) VALUES "
        "(1, 1, 'assistant', 'Dodałem mleko.', now()), (2, 1, 'user', 'kup chleb', now())",
    )
    tables = (*EXISTING_TABLES, *HISTORY_TABLES, *RECIPE_TABLES, "household_preferences")
    before = await snapshot(empty_database, tables)

    await migrate(empty_database, "up", "0012")

    engine = create_async_engine(empty_database)
    async with engine.begin() as connection:
        # Dotychczasowe prywatne rozmowy trafiają do archiwum; nic nie znika.
        archived = (
            await connection.execute(text("SELECT content, private FROM chat_messages ORDER BY id"))
        ).all()
        users = (
            await connection.execute(
                text("SELECT login, name, chat_hidden_before FROM users ORDER BY id")
            )
        ).all()
        # Nowe wiadomości domyślnie należą do wątku gospodarstwa.
        await connection.execute(
            text(
                "INSERT INTO chat_messages (user_id, household_id, role, content, created_at) "
                "VALUES (1, 1, 'user', 'nowa', now())"
            )
        )
        new_private = await connection.scalar(
            text("SELECT private FROM chat_messages WHERE content = 'nowa'")
        )
        await connection.execute(text("DELETE FROM chat_messages WHERE content = 'nowa'"))
        await connection.execute(text("UPDATE users SET name = 'Ala' WHERE id = 1"))
    await engine.dispose()
    assert archived == [("kup mleko", True), ("Dodałem mleko.", True), ("kup chleb", True)]
    assert users == [("ala", None, None), ("ola", None, None)]
    assert new_private is False

    await migrate(empty_database, "down", "0011")

    # Kolumny znikają (z imionami), wiadomości wracają do prywatnych wątków bez zmian.
    assert await snapshot(empty_database, tables) == before

    await migrate(empty_database, "up", "head")
    rows = (await snapshot(empty_database, ("chat_messages",)))["chat_messages"]
    assert [row[-1] for row in rows] == [True, True, True]

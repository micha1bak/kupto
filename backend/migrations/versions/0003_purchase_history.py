"""purchase history

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-22

Wyłącznie addytywna: tworzy trzy nowe, puste tabele historii zakupów i nie zmienia istniejących.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Typy enum `category` i `unit` istnieją od migracji 0001 — tu tylko się do nich odwołujemy.
category = postgresql.ENUM(name="category", create_type=False)
unit = postgresql.ENUM(name="unit", create_type=False)


def upgrade() -> None:
    op.create_table(
        "shopping_trips",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("household_id", sa.Integer(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_by_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name="fk_shopping_trips_household_id_households",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["finished_by_id"],
            ["users.id"],
            name="fk_shopping_trips_finished_by_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_shopping_trips"),
    )
    op.create_index(
        "ix_shopping_trips_household_id_finished_at",
        "shopping_trips",
        ["household_id", "finished_at"],
    )
    op.create_table(
        "purchased_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trip_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("normalized_name", sa.String(100), nullable=False),
        sa.Column("category", category, nullable=False),
        sa.Column("bought_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bought_by_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["trip_id"],
            ["shopping_trips.id"],
            name="fk_purchased_items_trip_id_shopping_trips",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["bought_by_id"],
            ["users.id"],
            name="fk_purchased_items_bought_by_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_purchased_items"),
    )
    op.create_index("ix_purchased_items_trip_id", "purchased_items", ["trip_id"])
    op.create_index("ix_purchased_items_bought_by_id", "purchased_items", ["bought_by_id"])
    op.create_table(
        "purchased_needs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("purchased_item_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Numeric(10, 3), nullable=True),
        sa.Column("unit", unit, nullable=True),
        sa.Column("note", sa.String(200), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["purchased_item_id"],
            ["purchased_items.id"],
            name="fk_purchased_needs_purchased_item_id_purchased_items",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_purchased_needs_user_id_users", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_purchased_needs"),
    )
    op.create_index(
        "ix_purchased_needs_purchased_item_id", "purchased_needs", ["purchased_item_id"]
    )


def downgrade() -> None:
    # Usuwa tylko tabele historii (wraz z zapisaną w nich historią); reszta danych zostaje.
    op.drop_table("purchased_needs")
    op.drop_table("purchased_items")
    op.drop_table("shopping_trips")

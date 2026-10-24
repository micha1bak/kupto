"""meal plan

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-24

Wyłącznie addytywna: tworzy nową, pustą tabelę planu obiadów gospodarstw (#44) i nie zmienia
istniejących.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "meal_plan_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("household_id", sa.Integer(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("recipe_id", sa.Integer(), nullable=True),
        sa.Column("planned_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name="fk_meal_plan_entries_household_id_households",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recipe_id"],
            ["recipes.id"],
            name="fk_meal_plan_entries_recipe_id_recipes",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["planned_by_id"],
            ["users.id"],
            name="fk_meal_plan_entries_planned_by_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_meal_plan_entries"),
        # Jeden obiad na dzień; indeks unikalności obsługuje też odczyt zakresu dat.
        sa.UniqueConstraint("household_id", "day", name="uq_meal_plan_entries_household_id"),
    )
    op.create_index("ix_meal_plan_entries_recipe_id", "meal_plan_entries", ["recipe_id"])


def downgrade() -> None:
    # Gubi plany obiadów gospodarstw — przed cofnięciem na produkcji zrób kopię tabeli.
    op.drop_table("meal_plan_entries")

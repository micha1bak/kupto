"""household recipes

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-22

Wyłącznie addytywna: tworzy dwie nowe, puste tabele bazy przepisów gospodarstwa (#46)
i nie zmienia istniejących.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Typy enum `category` i `unit` istnieją od migracji 0001 — tu tylko się do nich odwołujemy.
category = postgresql.ENUM(name="category", create_type=False)
unit = postgresql.ENUM(name="unit", create_type=False)


def upgrade() -> None:
    op.create_table(
        "recipes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("household_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("normalized_name", sa.String(100), nullable=False),
        sa.Column("servings", sa.String(50), nullable=True),
        sa.Column("source_url", sa.String(2000), nullable=True),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name="fk_recipes_household_id_households",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name="fk_recipes_created_by_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_recipes"),
        sa.UniqueConstraint("household_id", "normalized_name", name="uq_recipes_household_id"),
    )
    op.create_table(
        "recipe_ingredients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("amount", sa.Numeric(10, 3), nullable=True),
        sa.Column("unit", unit, nullable=True),
        sa.Column("note", sa.String(200), nullable=True),
        sa.Column("category", category, nullable=True),
        sa.ForeignKeyConstraint(
            ["recipe_id"],
            ["recipes.id"],
            name="fk_recipe_ingredients_recipe_id_recipes",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_recipe_ingredients"),
    )
    op.create_index("ix_recipe_ingredients_recipe_id", "recipe_ingredients", ["recipe_id"])


def downgrade() -> None:
    # Gubi zapisane przepisy gospodarstw — przed cofnięciem na produkcji zrób kopię tabel.
    op.drop_table("recipe_ingredients")
    op.drop_table("recipes")

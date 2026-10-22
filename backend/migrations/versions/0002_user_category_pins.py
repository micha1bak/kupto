"""user category pins

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Typ enum `category` istnieje od migracji 0001 — tu tylko się do niego odwołujemy.
category = postgresql.ENUM(name="category", create_type=False)


def upgrade() -> None:
    op.create_table(
        "user_category_pins",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("category", category, nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_category_pins_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "category", name="pk_user_category_pins"),
        sa.UniqueConstraint("user_id", "position", name="uq_user_category_pins_user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_category_pins")

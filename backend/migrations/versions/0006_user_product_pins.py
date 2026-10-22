"""user product pins

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-22

Wyłącznie addytywna: tworzy nową, pustą tabelę przypięć produktów i nie zmienia istniejących.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Typ enum `category` istnieje od migracji 0001 — tu tylko się do niego odwołujemy.
category = postgresql.ENUM(name="category", create_type=False)


def upgrade() -> None:
    op.create_table(
        "user_product_pins",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("normalized_name", sa.String(100), nullable=False),
        sa.Column("category", category, nullable=False),
        sa.Column("after_name", sa.String(100), nullable=True),
        sa.Column("at_end", sa.Boolean(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_product_pins_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "normalized_name", name="pk_user_product_pins"),
        sa.UniqueConstraint("user_id", "category", "position", name="uq_user_product_pins_user_id"),
    )


def downgrade() -> None:
    # Gubi tylko ręczną kolejność produktów — lista wraca do kolejności alfabetycznej.
    op.drop_table("user_product_pins")

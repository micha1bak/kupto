"""household preferences

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-24

Wyłącznie addytywna: tworzy nową, pustą tabelę preferencji gospodarstw (#45) i nie zmienia
istniejących. Brak wiersza oznacza gospodarstwo bez preferencji.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _text_list(name: str) -> sa.Column:
    return sa.Column(
        name, postgresql.ARRAY(sa.String(50)), nullable=False, server_default=sa.text("'{}'")
    )


def upgrade() -> None:
    op.create_table(
        "household_preferences",
        sa.Column("household_id", sa.Integer(), nullable=False),
        sa.Column("people", sa.SmallInteger(), nullable=True),
        _text_list("diets"),
        _text_list("excluded"),
        _text_list("disliked"),
        sa.Column("max_cooking_minutes", sa.SmallInteger(), nullable=True),
        sa.Column("notes", sa.String(300), nullable=True),
        sa.Column("updated_by_id", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name="fk_household_preferences_household_id_households",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            name="fk_household_preferences_updated_by_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("household_id", name="pk_household_preferences"),
    )


def downgrade() -> None:
    # Gubi preferencje gospodarstw — asystent wraca do propozycji bez nich.
    op.drop_table("household_preferences")

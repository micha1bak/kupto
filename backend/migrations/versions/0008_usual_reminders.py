"""usual reminders

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-22

Wyłącznie addytywna: tworzy nową, pustą tabelę przypomnień o zwykłych produktach (#40)
i nie zmienia istniejących.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usual_reminders",
        sa.Column("household_id", sa.Integer(), nullable=False),
        sa.Column("normalized_name", sa.String(100), nullable=False),
        sa.Column("reminded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name="fk_usual_reminders_household_id_households",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("household_id", "normalized_name", name="pk_usual_reminders"),
    )


def downgrade() -> None:
    # Gubi tylko pamięć wysłanych przypomnień — produkty mogą zostać przypomniane ponownie.
    op.drop_table("usual_reminders")

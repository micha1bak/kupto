"""notification preferences

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-22

Wyłącznie addytywna: tworzy nową, pustą tabelę ustawień powiadomień i nie zmienia istniejących.
Typ powiadomienia to tekst, a nie enum bazy, więc kolejne typy (np. #40) nie wymagają migracji.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notification_preferences",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(40), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_notification_preferences_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "type", name="pk_notification_preferences"),
    )


def downgrade() -> None:
    # Gubi tylko wybory użytkowników — wszyscy wracają do wartości domyślnych (wszystko włączone).
    op.drop_table("notification_preferences")

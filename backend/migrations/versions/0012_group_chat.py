"""group chat

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-24

Czat grupowy gospodarstwa (#78), bez przenoszenia danych:

- `users.name` (NULL = konto sprzed zmiany, poprosi o imię po zalogowaniu),
- `users.chat_hidden_before` (NULL = nic nie ukryto),
- `chat_messages.private`: wszystkie istniejące wiadomości to prywatne rozmowy sprzed czatu
  grupowego, więc dostają `true` (archiwum poza wątkiem gospodarstwa); nowe wiersze — `false`.
  Kolumna ze stałą wartością domyślną to w PostgreSQL 11+ zmiana katalogu, bez przepisywania
  tabeli,
- indeks `(household_id, created_at)` dla odczytu wątku gospodarstwa.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("name", sa.String(40), nullable=True))
    op.add_column(
        "users", sa.Column("chat_hidden_before", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "chat_messages",
        sa.Column("private", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.alter_column("chat_messages", "private", server_default=sa.false())
    op.create_index(
        "ix_chat_messages_household_id_created_at",
        "chat_messages",
        ["household_id", "created_at"],
    )


def downgrade() -> None:
    # Gubi imiona i znaczniki ukrycia historii. Wiadomości zostają: każda ma `user_id` autora
    # (przy odpowiedzi asystenta — autora prośby), więc wracają do prywatnych wątków.
    op.drop_index("ix_chat_messages_household_id_created_at", table_name="chat_messages")
    op.drop_column("chat_messages", "private")
    op.drop_column("users", "chat_hidden_before")
    op.drop_column("users", "name")

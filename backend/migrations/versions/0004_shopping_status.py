"""shopping status

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-22

Wyłącznie addytywna: dodaje do `users` kolumnę `shopping_since` dopuszczającą NULL. W PostgreSQL
to zmiana samego katalogu (bez przepisywania tabeli), a istniejące wiersze dostają NULL, czyli
„nie robi zakupów”.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("shopping_since", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Gubi tylko bieżące statusy zakupów; pozostałe dane użytkowników zostają.
    op.drop_column("users", "shopping_since")

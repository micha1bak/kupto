"""email auth

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-24

Logowanie e-mailem z weryfikacją i resetem hasła (#77), addytywnie:

- `users.email` (NULL = konto sprzed zmiany, które nie potwierdziło adresu) z unikalnym
  indeksem na `lower(email)`, `users.email_verified_at`, `users.verify_email_by`,
  `users.sessions_valid_after` — wszystkie NULL w istniejących wierszach, więc dodanie kolumn
  to zmiana katalogu bez przepisywania tabeli,
- `users.login` bez `NOT NULL` (konta zarejestrowane e-mailem nie mają loginu); istniejące
  loginy zostają i dalej działają przy logowaniu,
- tabele `auth_tokens` (jednorazowe tokeny z maili, tylko skróty) i `auth_rate_events`
  (limity prób).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email", sa.String(254), nullable=True))
    op.add_column(
        "users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("users", sa.Column("verify_email_by", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "users", sa.Column("sessions_valid_after", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index("uq_users_email_lower", "users", [sa.text("lower(email)")], unique=True)
    op.alter_column("users", "login", existing_type=sa.String(50), nullable=True)

    op.create_table(
        "auth_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("purpose", sa.String(20), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_auth_tokens_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_auth_tokens"),
        sa.UniqueConstraint("token_hash", name="uq_auth_tokens_token_hash"),
    )
    op.create_index("ix_auth_tokens_user_id", "auth_tokens", ["user_id"])

    op.create_table(
        "auth_rate_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_auth_rate_events"),
    )
    op.create_index(
        "ix_auth_rate_events_lookup", "auth_rate_events", ["action", "key_hash", "created_at"]
    )
    op.create_index("ix_auth_rate_events_created_at", "auth_rate_events", ["created_at"])


def downgrade() -> None:
    # Gubi adresy, potwierdzenia, tokeny i limity. Konta zarejestrowane e-mailem (bez loginu)
    # dostają login „<adres do 40 znaków>#<id>” — unikalny dzięki id i mieszczący się w 50 znakach.
    op.drop_table("auth_rate_events")
    op.drop_table("auth_tokens")
    op.execute("UPDATE users SET login = left(email, 40) || '#' || id WHERE login IS NULL")
    op.alter_column("users", "login", existing_type=sa.String(50), nullable=False)
    op.drop_index("uq_users_email_lower", table_name="users")
    op.drop_column("users", "sessions_valid_after")
    op.drop_column("users", "verify_email_by")
    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "email")

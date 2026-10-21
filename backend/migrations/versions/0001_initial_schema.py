"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CATEGORIES = (
    "Warzywa i owoce",
    "Pieczywo",
    "Nabiał",
    "Mięso i ryby",
    "Mrożonki",
    "Produkty suche",
    "Napoje",
    "Słodycze i przekąski",
    "Chemia i higiena",
    "Inne",
)
UNITS = ("szt", "kg", "g", "l", "ml", "opak")

category = postgresql.ENUM(*CATEGORIES, name="category", create_type=False)
unit = postgresql.ENUM(*UNITS, name="unit", create_type=False)


def upgrade() -> None:
    category.create(op.get_bind())
    unit.create(op.get_bind())

    op.create_table(
        "households",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_households"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("login", sa.String(50), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("household_id", sa.Integer(), nullable=True),
        sa.Column("joined_household_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name="fk_users_household_id_households",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("login", name="uq_users_login"),
    )
    op.create_index("ix_users_household_id", "users", ["household_id"])
    op.create_foreign_key(
        "fk_households_owner_id_users",
        "households",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_table(
        "shopping_lists",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("household_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name="fk_shopping_lists_household_id_households",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_shopping_lists"),
        sa.UniqueConstraint("household_id", name="uq_shopping_lists_household_id"),
    )
    op.create_table(
        "household_products",
        sa.Column("household_id", sa.Integer(), nullable=False),
        sa.Column("normalized_name", sa.String(100), nullable=False),
        sa.Column("category", category, nullable=False),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name="fk_household_products_household_id_households",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("household_id", "normalized_name", name="pk_household_products"),
    )
    op.create_table(
        "list_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("list_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("normalized_name", sa.String(100), nullable=False),
        sa.Column("category", category, nullable=False),
        sa.Column("bought_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("bought_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["bought_by_id"],
            ["users.id"],
            name="fk_list_items_bought_by_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["list_id"],
            ["shopping_lists.id"],
            name="fk_list_items_list_id_shopping_lists",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_list_items"),
        sa.UniqueConstraint("list_id", "normalized_name", name="uq_list_items_list_id"),
    )
    op.create_table(
        "needs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Numeric(10, 3), nullable=True),
        sa.Column("unit", unit, nullable=True),
        sa.Column("note", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["item_id"], ["list_items.id"], name="fk_needs_item_id_list_items", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_needs_user_id_users", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_needs"),
    )
    op.create_index("ix_needs_item_id", "needs", ["item_id"])
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("household_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name="fk_chat_messages_household_id_households",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_chat_messages_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_chat_messages"),
    )
    op.create_index(
        "ix_chat_messages_user_id_created_at", "chat_messages", ["user_id", "created_at"]
    )
    op.create_table(
        "chat_pending_actions",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_chat_pending_actions_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name="pk_chat_pending_actions"),
    )


def downgrade() -> None:
    op.drop_table("chat_pending_actions")
    op.drop_table("chat_messages")
    op.drop_table("needs")
    op.drop_table("list_items")
    op.drop_table("household_products")
    op.drop_table("shopping_lists")
    op.drop_constraint("fk_households_owner_id_users", "households", type_="foreignkey")
    op.drop_table("users")
    op.drop_table("households")
    unit.drop(op.get_bind())
    category.drop(op.get_bind())

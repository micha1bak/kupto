import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Enum,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kupto.db import Base, utcnow


class Category(enum.Enum):
    VEGETABLES_FRUITS = "Warzywa i owoce"
    BREAD = "Pieczywo"
    DAIRY = "Nabiał"
    MEAT_FISH = "Mięso i ryby"
    FROZEN = "Mrożonki"
    DRY_GOODS = "Produkty suche"
    DRINKS = "Napoje"
    SWEETS_SNACKS = "Słodycze i przekąski"
    HOUSEHOLD = "Chemia i higiena"
    OTHER = "Inne"


class Unit(enum.Enum):
    PCS = "szt"
    KG = "kg"
    G = "g"
    L = "l"
    ML = "ml"
    PACK = "opak"


def _enum(enum_cls: type[enum.Enum], name: str) -> Enum:
    return Enum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    household_id: Mapped[int | None] = mapped_column(
        ForeignKey("households.id", ondelete="SET NULL"), index=True
    )
    joined_household_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    household: Mapped["Household | None"] = relationship(
        back_populates="members", foreign_keys=[household_id]
    )


class Household(Base):
    __tablename__ = "households"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT", use_alter=True)
    )
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    members: Mapped[list[User]] = relationship(
        back_populates="household", foreign_keys=[User.household_id], passive_deletes=True
    )
    shopping_list: Mapped["ShoppingList"] = relationship(
        back_populates="household", cascade="all, delete-orphan", passive_deletes=True
    )


class ShoppingList(Base):
    __tablename__ = "shopping_lists"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), unique=True
    )

    household: Mapped[Household] = relationship(back_populates="shopping_list")
    items: Mapped[list["ListItem"]] = relationship(
        back_populates="shopping_list", cascade="all, delete-orphan", passive_deletes=True
    )


class ListItem(Base):
    __tablename__ = "list_items"
    __table_args__ = (UniqueConstraint("list_id", "normalized_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    list_id: Mapped[int] = mapped_column(ForeignKey("shopping_lists.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    normalized_name: Mapped[str] = mapped_column(String(100))
    category: Mapped[Category] = mapped_column(_enum(Category, "category"))
    bought_at: Mapped[datetime | None]
    bought_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    shopping_list: Mapped[ShoppingList] = relationship(back_populates="items")
    needs: Mapped[list["Need"]] = relationship(
        back_populates="item",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Need.created_at",
    )
    bought_by: Mapped[User | None] = relationship()


class Need(Base):
    __tablename__ = "needs"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(
        ForeignKey("list_items.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    unit: Mapped[Unit | None] = mapped_column(_enum(Unit, "unit"))
    note: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    item: Mapped[ListItem] = relationship(back_populates="needs")
    user: Mapped[User | None] = relationship()


class HouseholdProduct(Base):
    """Pamięć kategorii produktów skategoryzowanych wcześniej w gospodarstwie."""

    __tablename__ = "household_products"

    household_id: Mapped[int] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), primary_key=True
    )
    normalized_name: Mapped[str] = mapped_column(String(100), primary_key=True)
    category: Mapped[Category] = mapped_column(_enum(Category, "category"))


class UserCategoryPin(Base):
    """Kategoria przypięta przez użytkownika na danym miejscu jego kolejności kategorii.

    `position` to indeks w pełnej kolejności wszystkich kategorii (także pustych); nieprzypięte
    kategorie układają się wokół przypiętych w kolejności automatycznej.
    """

    __tablename__ = "user_category_pins"
    __table_args__ = (UniqueConstraint("user_id", "position"),)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    category: Mapped[Category] = mapped_column(_enum(Category, "category"), primary_key=True)
    position: Mapped[int] = mapped_column(SmallInteger)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (Index("ix_chat_messages_user_id_created_at", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class ChatPendingAction(Base):
    __tablename__ = "chat_pending_actions"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    action: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

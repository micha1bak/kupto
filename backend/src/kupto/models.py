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
    # Początek statusu „robię zakupy”; NULL = brak statusu. Aktywność (z wygasaniem) oceniaj
    # wyłącznie przez `kupto.lists.shopping_status`, nie bezpośrednio z tej kolumny.
    shopping_since: Mapped[datetime | None]
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


class UserProductPin(Base):
    """Produkt przypięty przez użytkownika na wybranym miejscu w obrębie kategorii.

    Kluczem jest znormalizowana nazwa produktu, więc przypięcie działa przy każdym kolejnym
    dodaniu produktu. Miejsce to kotwica — nieprzypięty produkt `after_name`, za którym stoi
    przypięty (`None` = początek kategorii, `at_end` = koniec) — oraz `position`, ranga wśród
    przypięć użytkownika w kategorii (`kupto.lists.ordering.arrange_anchored`).
    """

    __tablename__ = "user_product_pins"
    __table_args__ = (UniqueConstraint("user_id", "category", "position"),)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    normalized_name: Mapped[str] = mapped_column(String(100), primary_key=True)
    category: Mapped[Category] = mapped_column(_enum(Category, "category"))
    after_name: Mapped[str | None] = mapped_column(String(100))
    at_end: Mapped[bool] = mapped_column(default=False)
    position: Mapped[int] = mapped_column(SmallInteger)


class ShoppingTrip(Base):
    """Jedno zakończenie zakupów w gospodarstwie — nagłówek wpisu w historii zakupów."""

    __tablename__ = "shopping_trips"
    __table_args__ = (
        Index("ix_shopping_trips_household_id_finished_at", "household_id", "finished_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"))
    finished_at: Mapped[datetime] = mapped_column(default=utcnow)
    finished_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    items: Mapped[list["PurchasedItem"]] = relationship(
        back_populates="trip",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="PurchasedItem.id",
    )


class PurchasedItem(Base):
    """Kupiona pozycja przeniesiona z listy do historii — kopia stanu z chwili zakończenia."""

    __tablename__ = "purchased_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    trip_id: Mapped[int] = mapped_column(
        ForeignKey("shopping_trips.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    normalized_name: Mapped[str] = mapped_column(String(100))
    category: Mapped[Category] = mapped_column(_enum(Category, "category"))
    bought_at: Mapped[datetime]
    bought_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    trip: Mapped[ShoppingTrip] = relationship(back_populates="items")
    needs: Mapped[list["PurchasedNeed"]] = relationship(
        back_populates="item",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="PurchasedNeed.requested_at",
    )


class PurchasedNeed(Base):
    """Zapotrzebowanie, które doprowadziło do zakupu pozycji z historii."""

    __tablename__ = "purchased_needs"

    id: Mapped[int] = mapped_column(primary_key=True)
    purchased_item_id: Mapped[int] = mapped_column(
        ForeignKey("purchased_items.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    unit: Mapped[Unit | None] = mapped_column(_enum(Unit, "unit"))
    note: Mapped[str | None] = mapped_column(String(200))
    requested_at: Mapped[datetime]

    item: Mapped[PurchasedItem] = relationship(back_populates="needs")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (Index("ix_chat_messages_user_id_created_at", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class PushSubscription(Base):
    """Subskrypcja Web Push jednego urządzenia (przeglądarki) użytkownika.

    `endpoint` jest unikalny: urządzenie należy do najwyżej jednego użytkownika, a ponowny zapis
    przepina je na zalogowanego.
    """

    __tablename__ = "push_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    endpoint: Mapped[str] = mapped_column(Text, unique=True)
    p256dh: Mapped[str] = mapped_column(String(200))
    auth: Mapped[str] = mapped_column(String(100))
    user_agent: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow)


class NotificationPreference(Base):
    """Wybór użytkownika: czy chce dostawać powiadomienia danego typu (na wszystkich urządzeniach).

    Wiersz istnieje tylko po zmianie przez użytkownika; brak wiersza = wartość domyślna typu
    (`kupto.push.preferences.DEFAULT_ENABLED`). `type` to tekst (wartość `NotificationType`),
    a nie enum bazy — nowy typ powiadomienia nie wymaga migracji.
    """

    __tablename__ = "notification_preferences"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    type: Mapped[str] = mapped_column(String(40), primary_key=True)
    enabled: Mapped[bool]
    updated_at: Mapped[datetime] = mapped_column(default=utcnow)


class UsualReminder(Base):
    """Kiedy gospodarstwo dostało ostatnio przypomnienie push o zwykłym produkcie (#40).

    Najnowszy `reminded_at` gospodarstwa to chwila ostatniego przypomnienia (limit dzienny);
    produkt wraca w przypomnieniu dopiero po kolejnym zakupie (`kupto.history.reminders`).
    """

    __tablename__ = "usual_reminders"

    household_id: Mapped[int] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), primary_key=True
    )
    normalized_name: Mapped[str] = mapped_column(String(100), primary_key=True)
    reminded_at: Mapped[datetime]


class Recipe(Base):
    """Przepis zapisany w bazie przepisów gospodarstwa (#46) — wspólny dla wszystkich członków.

    Identyfikator jest stały (edycja zmienia przepis w miejscu), więc mogą się do niego odwoływać
    inne funkcje, np. plan posiłków (#44). Nazwa unikalna w gospodarstwie (bez wielkości liter).
    """

    __tablename__ = "recipes"
    __table_args__ = (UniqueConstraint("household_id", "normalized_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    normalized_name: Mapped[str] = mapped_column(String(100))
    # Tekst, nie liczba: „4 porcje”, „10 sztuk”, „blacha 20×30” (jak schema.org `recipeYield`).
    servings: Mapped[str | None] = mapped_column(String(50))
    source_url: Mapped[str | None] = mapped_column(String(2000))
    instructions: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow)

    ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        back_populates="recipe",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="RecipeIngredient.position",
    )
    created_by: Mapped[User | None] = relationship()


class RecipeIngredient(Base):
    """Składnik przepisu — pola jak w zapotrzebowaniu, więc trafia na listę bez przeliczeń.

    Miary kuchenne bez jednostki listy (łyżka, szklanka) są w `note`, a `amount`/`unit` puste.
    """

    __tablename__ = "recipe_ingredients"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(SmallInteger)
    name: Mapped[str] = mapped_column(String(100))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    unit: Mapped[Unit | None] = mapped_column(_enum(Unit, "unit"))
    note: Mapped[str | None] = mapped_column(String(200))
    category: Mapped[Category | None] = mapped_column(_enum(Category, "category"))

    recipe: Mapped[Recipe] = relationship(back_populates="ingredients")


class ChatPendingAction(Base):
    __tablename__ = "chat_pending_actions"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    action: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

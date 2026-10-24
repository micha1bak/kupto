from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from kupto.lists.category_order import AUTOMATIC, CategoryOrder
from kupto.lists.product_order import BASE, ProductOrder
from kupto.lists.quantities import aggregate_quantities
from kupto.lists.shopping_status import Shopper
from kupto.models import Category, ListItem, ShoppingList, Unit, display_name


class NeedCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100, pattern=r"\S")
    amount: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=3)
    unit: Unit | None = None
    note: str | None = Field(default=None, max_length=200)
    category: Category | None = None


class NeedUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=3)
    unit: Unit | None = None
    note: str | None = Field(default=None, max_length=200)


class CategoryMove(BaseModel):
    """Sąsiedzi przeniesionej kategorii na liście klienta; brak sąsiada = początek albo koniec."""

    after: Category | None = None
    before: Category | None = None


class ItemMove(BaseModel):
    """Sąsiedzi przeniesionej pozycji w jej grupie na liście klienta (identyfikatory pozycji);
    brak `after` = początek kategorii, brak `before` = koniec."""

    after: int | None = None
    before: int | None = None


class QuantityOut(BaseModel):
    amount: float
    unit: Unit | None


class NeedOut(BaseModel):
    id: int
    user_id: int | None
    name: str | None  # imię autora (`display_name`); None po usunięciu konta
    amount: float | None
    unit: Unit | None
    note: str | None
    created_at: datetime


class ItemOut(BaseModel):
    id: int
    name: str
    category: Category
    quantities: list[QuantityOut]
    needs: list[NeedOut]
    bought: bool
    bought_at: datetime | None
    bought_by: str | None
    # Produkt przypięty przez zalogowanego użytkownika na swoim miejscu w kategorii.
    pinned: bool = False


class CategoryGroup(BaseModel):
    category: Category
    pinned: bool
    items: list[ItemOut]


class CategoryOrderEntry(BaseModel):
    category: Category
    pinned: bool


class ShopperOut(BaseModel):
    """Członek gospodarstwa, który teraz robi zakupy."""

    user_id: int
    name: str  # imię (`display_name`)
    since: datetime
    expires_at: datetime


class ListOut(BaseModel):
    id: int
    groups: list[CategoryGroup]
    # Aktywne statusy „robię zakupy” członków gospodarstwa, najdawniej rozpoczęty pierwszy.
    shoppers: list[ShopperOut] = []


def item_out(item: ListItem, pinned: bool = False) -> ItemOut:
    return ItemOut(
        id=item.id,
        name=item.name,
        category=item.category,
        quantities=[
            QuantityOut(amount=float(q.amount), unit=q.unit)
            for q in aggregate_quantities((n.amount, n.unit) for n in item.needs)
        ],
        needs=[
            NeedOut(
                id=n.id,
                user_id=n.user_id,
                name=display_name(n.user) if n.user else None,
                amount=float(n.amount) if n.amount is not None else None,
                unit=n.unit,
                note=n.note,
                created_at=n.created_at,
            )
            for n in item.needs
        ],
        bought=item.bought_at is not None,
        bought_at=item.bought_at,
        bought_by=display_name(item.bought_by) if item.bought_by else None,
        pinned=pinned,
    )


def list_out(
    shopping_list: ShoppingList,
    order: CategoryOrder = AUTOMATIC,
    shoppers: Sequence[Shopper] = (),
    products: ProductOrder = BASE,
) -> ListOut:
    """Lista pogrupowana według kategorii w kolejności `order`; w grupie pozycje w kolejności
    produktów `products` (bez przypięć — bazowej: wyuczonej albo alfabetycznej)."""
    groups = []
    for category in order.categories:
        items = products.arrange(
            category, (i for i in shopping_list.items if i.category == category)
        )
        if items:
            groups.append(
                CategoryGroup(
                    category=category,
                    pinned=category in order.pinned,
                    items=[item_out(i, products.is_pinned(i)) for i in items],
                )
            )
    return ListOut(
        id=shopping_list.id,
        groups=groups,
        shoppers=[
            ShopperOut(user_id=s.user_id, name=s.name, since=s.since, expires_at=s.expires_at)
            for s in shoppers
        ],
    )


def category_order_out(order: CategoryOrder) -> list[CategoryOrderEntry]:
    return [CategoryOrderEntry(category=c, pinned=c in order.pinned) for c in order.categories]

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from kupto.lists.quantities import aggregate_quantities
from kupto.models import Category, ListItem, ShoppingList, Unit


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


class QuantityOut(BaseModel):
    amount: float
    unit: Unit | None


class NeedOut(BaseModel):
    id: int
    user_id: int | None
    login: str | None
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


class CategoryGroup(BaseModel):
    category: Category
    items: list[ItemOut]


class ListOut(BaseModel):
    id: int
    groups: list[CategoryGroup]


def item_out(item: ListItem) -> ItemOut:
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
                login=n.user.login if n.user else None,
                amount=float(n.amount) if n.amount is not None else None,
                unit=n.unit,
                note=n.note,
                created_at=n.created_at,
            )
            for n in item.needs
        ],
        bought=item.bought_at is not None,
        bought_at=item.bought_at,
        bought_by=item.bought_by.login if item.bought_by else None,
    )


def list_out(shopping_list: ShoppingList) -> ListOut:
    """Lista pogrupowana według kategorii w stałej kolejności; w grupie pozycje alfabetycznie."""
    groups = []
    for category in Category:
        items = sorted(
            (i for i in shopping_list.items if i.category == category),
            key=lambda i: i.normalized_name,
        )
        if items:
            groups.append(CategoryGroup(category=category, items=[item_out(i) for i in items]))
    return ListOut(id=shopping_list.id, groups=groups)

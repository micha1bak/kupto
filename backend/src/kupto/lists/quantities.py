import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from kupto.models import Unit


def clean_name(name: str) -> str:
    return " ".join(unicodedata.normalize("NFC", name).split())


def normalize_name(name: str) -> str:
    return clean_name(name).lower()


@dataclass(frozen=True)
class Quantity:
    amount: Decimal
    unit: Unit | None


def aggregate_quantities(needs: Iterable[tuple[Decimal | None, Unit | None]]) -> list[Quantity]:
    """Sumuje ilości w tej samej jednostce; różne jednostki zostają osobno."""
    totals: dict[Unit | None, Decimal] = {}
    for amount, unit in needs:
        if amount is not None:
            totals[unit] = totals.get(unit, Decimal(0)) + amount
    return [Quantity(amount=_plain(amount), unit=unit) for unit, amount in totals.items()]


def _plain(amount: Decimal) -> Decimal:
    """Usuwa zbędne zera bez notacji wykładniczej: 10.000 → 10 (nie 1E+1), 0.500 → 0.5."""
    normalized = amount.normalize()
    return normalized.quantize(Decimal(1)) if normalized == normalized.to_integral() else normalized

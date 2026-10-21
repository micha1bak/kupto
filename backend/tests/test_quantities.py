from decimal import Decimal

from kupto.lists.quantities import Quantity, aggregate_quantities, clean_name, normalize_name
from kupto.models import Unit


def test_normalize_name_ignores_case_and_whitespace():
    assert normalize_name("  Mleko   Bez\tLaktozy ") == "mleko bez laktozy"
    assert normalize_name("MLEKO") == normalize_name(" mleko ")


def test_normalize_name_unifies_unicode_forms():
    decomposed = "żółty ser"  # „żółty” zapisane znakami łączonymi
    assert normalize_name(decomposed) == normalize_name("żółty ser")


def test_clean_name_keeps_case():
    assert clean_name("  Ser   żółty ") == "Ser żółty"


def test_same_units_are_summed():
    result = aggregate_quantities([(Decimal("1"), Unit.L), (Decimal("2.000"), Unit.L)])

    assert result == [Quantity(Decimal("3"), Unit.L)]


def test_different_units_are_kept_separately_in_order():
    result = aggregate_quantities([(Decimal(2), Unit.PCS), (Decimal(1), Unit.KG)])

    assert result == [Quantity(Decimal(2), Unit.PCS), Quantity(Decimal(1), Unit.KG)]


def test_needs_without_amount_are_skipped():
    assert aggregate_quantities([(None, None), (None, Unit.L)]) == []

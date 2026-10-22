from kupto.lists.ordering import arrange

BASE = ["a", "b", "c", "d", "e"]


def test_without_pins_keeps_base_order():
    assert arrange(BASE, {}) == BASE


def test_pinned_elements_take_their_positions():
    assert arrange(BASE, {"e": 0}) == ["e", "a", "b", "c", "d"]
    assert arrange(BASE, {"a": 4}) == ["b", "c", "d", "e", "a"]
    assert arrange(BASE, {"d": 1}) == ["a", "d", "b", "c", "e"]


def test_unpinned_elements_fill_the_gaps_in_base_order():
    assert arrange(BASE, {"e": 0, "a": 2}) == ["e", "b", "a", "c", "d"]


def test_follows_a_changed_base_order_around_pins():
    # Wyuczona kolejność (#38) zmienia bazę — przypięte zostają na swoich miejscach.
    assert arrange(["d", "c", "b", "a", "e"], {"e": 0, "a": 2}) == ["e", "d", "a", "c", "b"]


def test_position_beyond_range_means_end_and_unknown_pins_are_ignored():
    assert arrange(["a", "b"], {"a": 7, "z": 0}) == ["b", "a"]

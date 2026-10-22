from kupto.lists.ordering import Anchor, arrange, arrange_anchored, learned

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


# Kotwice — kolejność produktów w kategorii, której zbiór się zmienia.

A = Anchor


def test_anchored_without_pins_keeps_base_order():
    assert arrange_anchored(BASE, {}) == BASE


def test_anchored_at_start_after_element_and_at_end():
    assert arrange_anchored(BASE, {"e": A(0)}) == ["e", "a", "b", "c", "d"]
    assert arrange_anchored(BASE, {"a": A(0, after="c")}) == ["b", "c", "a", "d", "e"]
    assert arrange_anchored(BASE, {"a": A(0, at_end=True)}) == ["b", "c", "d", "e", "a"]


def test_anchored_pins_stay_by_their_neighbour_when_the_set_grows():
    pins = {"e": A(0, after="b"), "a": A(1, at_end=True)}
    assert arrange_anchored(["a", "b", "c", "e"], pins) == ["b", "e", "c", "a"]
    # Nowe elementy przed kotwicą i za nią nie odrywają przypiętych od ich miejsc.
    grown = ["0", "a", "b", "c", "e", "z"]
    assert arrange_anchored(grown, pins) == ["0", "b", "e", "c", "z", "a"]


def test_anchored_rank_orders_pins_sharing_an_anchor():
    pins = {"d": A(2), "e": A(0), "c": A(1, after="a"), "b": A(3, after="a")}
    assert arrange_anchored(BASE, pins) == ["e", "d", "a", "c", "b"]


def test_anchored_follows_a_changed_base_order():
    # Wyuczona kolejność (#38) zmienia bazę — przypięte zostają za swoimi kotwicami.
    pins = {"e": A(0), "a": A(1, after="c")}
    assert arrange_anchored(["d", "c", "b", "a", "e"], pins) == ["e", "d", "c", "a", "b"]


def test_anchored_skips_absent_pins_and_keeps_orphans():
    # Kotwicy „x” nie ma w bazie, a „z” nie jest jej elementem — nic nie ginie ani nie dochodzi.
    pins = {"a": A(0, after="x"), "z": A(1), "b": A(2, at_end=True)}
    assert arrange_anchored(["a", "b", "c"], pins) == ["c", "a", "b"]


def test_learned_without_scores_is_base():
    assert learned(BASE, {}) == BASE


def test_learned_elements_swap_places_and_others_stay():
    # „b” i „d” bez wyniku zostają na miejscach 1 i 3; wyuczone zajmują miejsca 0, 2, 4.
    assert learned(BASE, {"a": 0.9, "c": 0.5, "e": 0.1}) == ["e", "b", "c", "d", "a"]


def test_learned_ties_keep_base_order_and_unknown_scores_are_skipped():
    assert learned(BASE, {"d": 0.5, "b": 0.5, "a": 0.7, "x": 0.0}) == ["b", "d", "c", "a", "e"]

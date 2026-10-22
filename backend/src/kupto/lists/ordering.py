"""Kolejność elementów listy: przypięcia użytkownika mają pierwszeństwo przed kolejnością bazową.

Kolejność bazowa to kolejność wyuczona z historii odhaczeń (`learned`) na tle stałej kolejności
kategorii albo alfabetycznej kolejności produktów (zmiana learned-order).
"""

from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass


def arrange[T: Hashable](base: Sequence[T], pins: Mapping[T, int]) -> list[T]:
    """Ustawia przypięte elementy na ich miejscach, a resztę w kolejności bazowej wokół nich.

    Przypięcia spoza `base` są pomijane, a miejsce poza zakresem oznacza koniec. Miejsce jest
    stabilne tylko w stałym zbiorze (kategorie); dla zbiorów, które rosną i maleją (produkty),
    służy `arrange_anchored`.
    """
    present = set(base)
    result = [element for element in base if element not in pins]
    for element, position in sorted(pins.items(), key=lambda pin: pin[1]):
        if element in present:
            result.insert(min(position, len(result)), element)
    return result


def learned[T: Hashable](base: Sequence[T], scores: Mapping[T, float]) -> list[T]:
    """Kolejność wyuczona: elementy z wynikiem zamieniają się miejscami według wyniku.

    Elementy z wynikiem zajmują te same miejsca w `base` co dotąd, ułożone między sobą rosnąco
    po wyniku (remis — kolejność w `base`); pozostałe zostają dokładnie na swoich miejscach.
    Bez wyników zwraca `base` bez zmian (design D4 zmiany learned-order).
    """
    ranked = iter(
        sorted((element for element in base if element in scores), key=scores.__getitem__)
    )
    return [next(ranked) if element in scores else element for element in base]


@dataclass(frozen=True)
class Anchor[T]:
    """Miejsce przypiętego elementu względem nieprzypiętych.

    `after` — nieprzypięty element, bezpośrednio za którym stoi przypięty; `None` oznacza
    początek, a `at_end` — koniec. `rank` porządkuje przypięte elementy między sobą.
    """

    rank: int
    after: T | None = None
    at_end: bool = False


def arrange_anchored[T: Hashable](base: Sequence[T], pins: Mapping[T, Anchor[T]]) -> list[T]:
    """Układa nieprzypięte elementy w kolejności bazowej, a przypięte za ich kotwicami.

    W odróżnieniu od `arrange` przypięcie nie jest numerem miejsca, więc zostaje przy swoim
    sąsiedzie, gdy zbiór elementów się zmienia (np. nowe produkty w kategorii). Przypięcia spoza
    `base` są pomijane; przypięcie z kotwicą, która nie jest nieprzypiętym elementem `base`,
    trafia przed elementy przypięte na końcu, więc żaden element nie ginie.
    """
    present = set(base)
    unpinned = [element for element in base if element not in pins]
    following: dict[T, list[T]] = {element: [] for element in unpinned}
    start: list[T] = []
    orphans: list[T] = []
    end: list[T] = []
    for element, anchor in sorted(pins.items(), key=lambda pin: pin[1].rank):
        if element not in present:
            continue
        if anchor.at_end:
            end.append(element)
        elif anchor.after is None:
            start.append(element)
        elif anchor.after in following:
            following[anchor.after].append(element)
        else:
            orphans.append(element)
    result = start
    for element in unpinned:
        result.append(element)
        result.extend(following[element])
    return result + orphans + end

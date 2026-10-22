"""Kolejność elementów listy: przypięcia użytkownika mają pierwszeństwo przed kolejnością bazową.

Kolejność bazowa to dziś stała kolejność kategorii; docelowo kolejność wyuczona (#38).
"""

from collections.abc import Hashable, Mapping, Sequence


def arrange[T: Hashable](base: Sequence[T], pins: Mapping[T, int]) -> list[T]:
    """Ustawia przypięte elementy na ich miejscach, a resztę w kolejności bazowej wokół nich.

    Przypięcia spoza `base` są pomijane, a miejsce poza zakresem oznacza koniec — dzięki temu
    funkcja działa także dla zbiorów zmiennej wielkości (np. produktów w kategorii).
    """
    present = set(base)
    result = [element for element in base if element not in pins]
    for element, position in sorted(pins.items(), key=lambda pin: pin[1]):
        if element in present:
            result.insert(min(position, len(result)), element)
    return result

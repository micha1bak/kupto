"""Wyciąganie przepisu ze strony HTML.

Najpierw dane strukturalne schema.org/Recipe (JSON-LD), które większość serwisów z przepisami
publikuje dla wyszukiwarek — dają czystą listę składników. Gdy ich nie ma, zwracamy widoczny
tekst strony (przycięty), z którego składniki wyciąga model.
"""

import html
import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any

MAX_INGREDIENTS = 60
MAX_FIELD_CHARS = 200
MAX_TEXT_CHARS = 6000

_SKIPPED_TAGS = {"script", "style", "noscript", "template", "svg", "iframe", "nav"}
_BLOCK_TAGS = {
    "p", "div", "li", "ul", "ol", "br", "tr", "td", "th", "table", "section", "article",
    "header", "footer", "h1", "h2", "h3", "h4", "h5", "h6", "dt", "dd", "main", "aside",
}  # fmt: skip
_TAG = re.compile(r"<[^>]+>")
_SPACES = re.compile(r"[ \t\r\f\v ]+")
_BLANK_LINES = re.compile(r"\n\s*\n+")
_INGREDIENTS_HEADING = re.compile(r"składniki|ingredients", re.IGNORECASE)
_DIGIT = re.compile(r"\d")


@dataclass(frozen=True)
class Recipe:
    name: str | None
    servings: str | None
    ingredients: list[str]


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.json_ld: list[str] = []
        self.title: list[str] = []
        self.text: list[str] = []
        self._skip_depth = 0
        self._in_json_ld = False
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script" and (dict(attrs).get("type") or "").lower() == "application/ld+json":
            self._in_json_ld = True
            self.json_ld.append("")
        if tag == "title":
            self._in_title = True
        if tag in _SKIPPED_TAGS:
            self._skip_depth += 1
        elif tag in _BLOCK_TAGS:
            self.text.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self._in_json_ld = False
        if tag == "title":
            self._in_title = False
        if tag in _SKIPPED_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag in _BLOCK_TAGS:
            self.text.append("\n")

    def handle_data(self, data: str) -> None:
        if self._in_json_ld:
            self.json_ld[-1] += data
        elif self._in_title:
            self.title.append(data)
        elif not self._skip_depth:
            self.text.append(data)


@dataclass(frozen=True)
class ParsedPage:
    title: str | None
    recipe: Recipe | None
    text: str


def parse_page(page_html: str) -> ParsedPage:
    parser = _PageParser()
    parser.feed(page_html)
    parser.close()
    recipe = None
    for block in parser.json_ld:
        try:
            data = json.loads(block)
        except ValueError:
            continue
        if (recipe := find_recipe(data)) is not None:
            break
    title = _clean(" ".join(parser.title)) or None
    return ParsedPage(title=title, recipe=recipe, text=_visible_text("".join(parser.text)))


def find_recipe(data: Any) -> Recipe | None:
    """Pierwszy obiekt schema.org Recipe ze składnikami (także w `@graph` i listach)."""
    if isinstance(data, list):
        for element in data:
            if (recipe := find_recipe(element)) is not None:
                return recipe
        return None
    if not isinstance(data, dict):
        return None
    types = data.get("@type")
    types = types if isinstance(types, list) else [types]
    if "Recipe" in types:
        raw = data.get("recipeIngredient") or data.get("ingredients") or []
        ingredients = [_clean(i) for i in (raw if isinstance(raw, list) else [raw])]
        ingredients = [i for i in ingredients if i][:MAX_INGREDIENTS]
        if ingredients:
            return Recipe(
                name=_clean(data.get("name")) or None,
                servings=_servings(data.get("recipeYield")),
                ingredients=ingredients,
            )
    for key in ("@graph", "mainEntity", "mainEntityOfPage"):
        if (recipe := find_recipe(data.get(key))) is not None:
            return recipe
    return None


def _servings(value: Any) -> str | None:
    if isinstance(value, list):
        # Często ["4", "4 porcje"] — dłuższy opis mówi więcej.
        value = max((str(v) for v in value), key=len, default=None)
    return _clean(value) or None


def _clean(value: Any) -> str:
    if not isinstance(value, str | int | float) or isinstance(value, bool):
        return ""
    text = html.unescape(_TAG.sub(" ", str(value)))
    return _SPACES.sub(" ", text).strip()[:MAX_FIELD_CHARS]


def _visible_text(raw: str) -> str:
    lines = (_SPACES.sub(" ", line).strip() for line in raw.split("\n"))
    text = _BLANK_LINES.sub("\n", "\n".join(line for line in lines if line))
    # Na rozbudowanych stronach składniki bywają daleko za menu — wtedy zaczynamy tuż przed nimi.
    # Nagłówek „Składniki” bywa też w menu kategorii — wybieramy ten, po którym są ilości.
    start = 0
    if len(text) > MAX_TEXT_CHARS:
        headings = [m.start() for m in _INGREDIENTS_HEADING.finditer(text)]
        with_amounts = [h for h in headings if _DIGIT.search(text, h, h + 300)]
        if chosen := (with_amounts or headings):
            start = max(0, chosen[0] - MAX_TEXT_CHARS // 10)
    return text[start : start + MAX_TEXT_CHARS]

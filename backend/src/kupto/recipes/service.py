import logging
from typing import Any

from kupto.recipes.extract import parse_page
from kupto.recipes.fetch import FetchError, fetch_page

logger = logging.getLogger(__name__)


async def recipe_from_url(url: str, **fetch_options: Any) -> dict[str, Any]:
    """Przepis spod adresu w zwięzłej postaci dla modelu albo `{"error": ...}`.

    `fetch_options` trafiają do `fetch_page` (w testach: resolver DNS i transport HTTP).
    """
    try:
        page = await fetch_page(url, **fetch_options)
    except FetchError as exc:
        logger.info("Nie pobrano strony z przepisem: %s", exc.message)
        return {"error": exc.message}
    parsed = parse_page(page.html)
    if parsed.recipe is not None:
        return {
            "source": "schema.org",
            "url": page.url,
            "name": parsed.recipe.name or parsed.title,
            "servings": parsed.recipe.servings,
            "ingredients": parsed.recipe.ingredients,
        }
    if not parsed.text:
        return {"error": "Na stronie nie ma tekstu, z którego można odczytać przepis."}
    return {"source": "page_text", "url": page.url, "title": parsed.title, "text": parsed.text}

import asyncio
import json

import httpx
import pytest

from kupto.recipes.extract import MAX_TEXT_CHARS, find_recipe, parse_page
from kupto.recipes.fetch import FetchError, fetch_page, is_public_address, validate_url
from kupto.recipes.service import recipe_from_url

PUBLIC_IP = "93.184.216.34"

RECIPE_LD = {
    "@context": "https://schema.org",
    "@graph": [
        {"@type": "WebPage", "name": "Naleśniki — Kuchnia"},
        {
            "@type": ["Recipe"],
            "name": "Naleśniki na mleku",
            "recipeYield": ["10", "10 sztuk"],
            "recipeIngredient": [
                "2 szklanki mąki",
                "0,5 l <b>mleka</b>",
                "2 jajka",
                "szczypta soli &amp; cukru",
            ],
        },
    ],
}


def recipe_html(ld=RECIPE_LD, body="<p>Smaż na patelni.</p>") -> str:
    return (
        "<html><head><title>Naleśniki | Kuchnia</title>"
        f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>'
        f"</head><body><nav>Menu</nav>{body}<script>var x = 1;</script></body></html>"
    )


def resolver_for(mapping: dict[str, list[str]]):
    async def resolve(host: str, port: int) -> list[str]:
        if host not in mapping:
            raise OSError("nie ma takiej nazwy")
        return mapping[host]

    return resolve


def site(handler):
    """Transport testowy; zapisuje każde żądanie, które naprawdę wyszłoby do sieci."""
    sent: list[httpx.Request] = []

    async def handle(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return await handler(request) if asyncio.iscoroutinefunction(handler) else handler(request)

    return httpx.MockTransport(handle), sent


def html_response(text: str, **headers) -> httpx.Response:
    return httpx.Response(
        200, headers={"content-type": "text/html; charset=utf-8", **headers}, text=text
    )


# --- adresy -----------------------------------------------------------------


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.1.2.3",
        "172.16.0.1",
        "192.168.1.1",
        "169.254.169.254",
        "100.64.0.1",
        "0.0.0.0",
        "224.0.0.1",
        "255.255.255.255",
        "::1",
        "::",
        "fc00::1",
        "fe80::1%eth0",
        "::ffff:127.0.0.1",
        "::ffff:169.254.169.254",
        "2002:7f00:1::",  # 6to4 z 127.0.0.1
        "ff02::1",
    ],
)
def test_private_and_local_addresses_are_not_public(address):
    assert not is_public_address(address)


@pytest.mark.parametrize("address", [PUBLIC_IP, "8.8.8.8", "2606:4700:4700::1111"])
def test_public_addresses(address):
    assert is_public_address(address)


@pytest.mark.parametrize(
    "url",
    [
        "ftp://przepisy.example/plik",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "gopher://przepisy.example/",
        "https://",
        "https://ala:haslo@przepisy.example/",
        "http://przepisy.example:8080/",
        "https://przepisy.example:22/",
        "przepisy.example/nalesniki",
    ],
)
def test_unsupported_urls_are_rejected(url):
    with pytest.raises(FetchError):
        validate_url(url)


def test_default_ports_are_allowed():
    assert validate_url(" https://przepisy.example:443/a ").host == "przepisy.example"
    assert validate_url("http://przepisy.example/a").scheme == "http"


# --- pobieranie -------------------------------------------------------------


async def test_page_is_fetched_from_checked_address_with_original_host():
    transport, sent = site(lambda request: html_response("<p>Przepis</p>"))

    page = await fetch_page(
        "https://przepisy.example/nalesniki?porcje=4",
        resolver=resolver_for({"przepisy.example": [PUBLIC_IP]}),
        transport=transport,
    )

    assert page.html == "<p>Przepis</p>"
    assert page.url == "https://przepisy.example/nalesniki?porcje=4"
    (request,) = sent
    # Połączenie na sprawdzony adres IP — bez drugiego rozwiązania nazwy przez klienta HTTP.
    assert request.url.host == PUBLIC_IP
    assert request.url.path == "/nalesniki"
    assert request.headers["host"] == "przepisy.example"
    assert request.extensions["sni_hostname"] == "przepisy.example"
    assert "cookie" not in request.headers


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/",
        "http://127.0.0.1/",
        "http://[::1]/",
        "http://169.254.169.254/latest/meta-data/",
        "http://192.168.0.1/",
        "http://wewnetrzny.example/",
    ],
)
async def test_private_targets_are_blocked_before_any_request(url):
    transport, sent = site(lambda request: html_response("tajne"))
    resolver = resolver_for({"localhost": ["127.0.0.1", "::1"], "wewnetrzny.example": ["10.0.0.5"]})

    with pytest.raises(FetchError, match="sieci prywatnej"):
        await fetch_page(url, resolver=resolver, transport=transport)

    assert sent == []


async def test_name_resolving_to_any_private_address_is_blocked():
    transport, sent = site(lambda request: html_response("tajne"))
    resolver = resolver_for({"mieszany.example": [PUBLIC_IP, "127.0.0.1"]})

    with pytest.raises(FetchError, match="sieci prywatnej"):
        await fetch_page("https://mieszany.example/", resolver=resolver, transport=transport)

    assert sent == []


@pytest.mark.parametrize(
    "location",
    [
        "http://169.254.169.254/latest/meta-data/",
        "http://wewnetrzny.example/admin",
        "file:///etc/passwd",
        "http://przepisy.example:6379/",
    ],
)
async def test_redirect_to_forbidden_target_is_blocked(location):
    transport, sent = site(lambda request: httpx.Response(302, headers={"location": location}))
    resolver = resolver_for(
        {"przepisy.example": [PUBLIC_IP], "wewnetrzny.example": ["192.168.1.10"]}
    )

    with pytest.raises(FetchError):
        await fetch_page("https://przepisy.example/", resolver=resolver, transport=transport)

    assert len(sent) == 1


async def test_relative_redirect_is_followed_and_checked_again():
    def handler(request):
        if request.url.path == "/stary":
            return httpx.Response(301, headers={"location": "/nowy"})
        return html_response("<p>nowy</p>")

    transport, sent = site(handler)
    page = await fetch_page(
        "https://przepisy.example/stary",
        resolver=resolver_for({"przepisy.example": [PUBLIC_IP]}),
        transport=transport,
    )

    assert page.url == "https://przepisy.example/nowy"
    assert [r.url.path for r in sent] == ["/stary", "/nowy"]


async def test_redirect_loop_is_cut():
    transport, sent = site(lambda request: httpx.Response(302, headers={"location": "/znowu"}))

    with pytest.raises(FetchError, match="zbyt wiele"):
        await fetch_page(
            "https://przepisy.example/",
            resolver=resolver_for({"przepisy.example": [PUBLIC_IP]}),
            transport=transport,
        )

    assert len(sent) == 6


async def test_too_large_page_is_rejected_while_reading():
    async def chunks():
        for _ in range(100):
            yield b"x" * 1000

    transport, _ = site(
        lambda request: httpx.Response(200, headers={"content-type": "text/html"}, content=chunks())
    )

    with pytest.raises(FetchError, match="zbyt duża"):
        await fetch_page(
            "https://przepisy.example/",
            resolver=resolver_for({"przepisy.example": [PUBLIC_IP]}),
            transport=transport,
            max_bytes=10_000,
        )


async def test_declared_too_large_page_is_rejected():
    transport, _ = site(lambda request: html_response("x", **{"content-length": "99999999"}))

    with pytest.raises(FetchError, match="zbyt duża"):
        await fetch_page(
            "https://przepisy.example/",
            resolver=resolver_for({"przepisy.example": [PUBLIC_IP]}),
            transport=transport,
        )


async def test_slow_page_times_out():
    async def handler(request):
        await asyncio.sleep(5)
        return html_response("za późno")

    transport, _ = site(handler)

    with pytest.raises(FetchError, match="na czas"):
        await fetch_page(
            "https://przepisy.example/",
            resolver=resolver_for({"przepisy.example": [PUBLIC_IP]}),
            transport=transport,
            time_limit=0.1,
        )


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(404, headers={"content-type": "text/html"}, text="brak"),
        httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"%PDF"),
    ],
)
async def test_errors_and_non_html_are_rejected(response):
    transport, _ = site(lambda request: response)

    with pytest.raises(FetchError):
        await fetch_page(
            "https://przepisy.example/",
            resolver=resolver_for({"przepisy.example": [PUBLIC_IP]}),
            transport=transport,
        )


async def test_dns_failure_is_reported():
    with pytest.raises(FetchError, match="DNS"):
        await fetch_page("https://nie-ma.example/", resolver=resolver_for({}))


async def test_charset_from_meta_tag_is_used():
    body = '<meta charset="iso-8859-2"><p>Mąka</p>'.encode("iso-8859-2")
    transport, _ = site(
        lambda request: httpx.Response(200, headers={"content-type": "text/html"}, content=body)
    )

    page = await fetch_page(
        "https://przepisy.example/",
        resolver=resolver_for({"przepisy.example": [PUBLIC_IP]}),
        transport=transport,
    )

    assert "Mąka" in page.html


# --- wyciąganie przepisu ----------------------------------------------------


def test_recipe_is_read_from_json_ld_graph():
    parsed = parse_page(recipe_html())

    assert parsed.title == "Naleśniki | Kuchnia"
    assert parsed.recipe is not None
    assert parsed.recipe.name == "Naleśniki na mleku"
    assert parsed.recipe.servings == "10 sztuk"
    assert parsed.recipe.ingredients == [
        "2 szklanki mąki",
        "0,5 l mleka",
        "2 jajka",
        "szczypta soli & cukru",
    ]


def test_recipe_in_list_and_without_ingredients():
    assert find_recipe([{"@type": "Organization"}, {"@type": "Recipe"}]) is None
    recipe = find_recipe([{"@type": "Recipe", "name": "Zupa", "recipeIngredient": ["woda"]}])
    assert recipe is not None and recipe.ingredients == ["woda"]


def test_invalid_json_ld_falls_back_to_text():
    page = (
        '<html><head><script type="application/ld+json">{nie json</script></head>'
        "<body><h1>Placki</h1><ul><li>3 ziemniaki</li><li>1 cebula</li></ul>"
        "<style>.x{}</style></body></html>"
    )

    parsed = parse_page(page)

    assert parsed.recipe is None
    assert parsed.text == "Placki\n3 ziemniaki\n1 cebula"


def test_long_text_starts_near_ingredients():
    body = (
        "<nav>Przepisy na obiad</nav>"
        "<div>Składniki</div><ul><li>Kasze</li><li>Ryż</li></ul>"  # menu kategorii, bez ilości
        "<p>" + "reklama " * 2000 + "</p><h2>Składniki</h2><ul><li>2 jajka</li></ul>"
    )

    parsed = parse_page(f"<html><body>{body}</body></html>")

    assert len(parsed.text) <= MAX_TEXT_CHARS
    assert "Składniki\n2 jajka" in parsed.text
    assert "Przepisy na obiad" not in parsed.text


async def test_recipe_from_url_returns_ingredients_or_text_or_error():
    resolver = resolver_for({"przepisy.example": [PUBLIC_IP]})
    pages = {
        "/ld": recipe_html(),
        "/tekst": "<html><body><h1>Placki</h1><p>3 ziemniaki</p></body></html>",
        "/pusta": "<html><body><script>x()</script></body></html>",
    }
    transport, _ = site(lambda request: html_response(pages[request.url.path]))

    async def get(path):
        return await recipe_from_url(
            f"https://przepisy.example{path}", resolver=resolver, transport=transport
        )

    assert await get("/ld") == {
        "source": "schema.org",
        "url": "https://przepisy.example/ld",
        "name": "Naleśniki na mleku",
        "servings": "10 sztuk",
        "ingredients": ["2 szklanki mąki", "0,5 l mleka", "2 jajka", "szczypta soli & cukru"],
    }
    assert await get("/tekst") == {
        "source": "page_text",
        "url": "https://przepisy.example/tekst",
        "title": None,
        "text": "Placki\n3 ziemniaki",
    }
    assert "error" in await get("/pusta")
    assert "sieci prywatnej" in (await recipe_from_url("http://127.0.0.1/"))["error"]

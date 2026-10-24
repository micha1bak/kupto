"""Bezpieczne pobieranie strony z linku podanego w czacie.

Link pochodzi od użytkownika (a pośrednio od modelu), więc serwer nie może dać się użyć do
odpytywania własnej sieci (SSRF). Zasady:

- tylko `http`/`https`, bez danych logowania w adresie i tylko na domyślnych portach;
- nazwa hosta jest rozwiązywana przez nas, a WSZYSTKIE jej adresy muszą być publiczne
  (`is_global`) — blokuje to localhost, sieci prywatne, link-local (169.254.169.254),
  CGNAT, multicast i adresy IPv4 zapisane jako IPv6;
- połączenie idzie na sprawdzony adres IP (nagłówek `Host` i SNI z oryginalnej nazwy), więc
  ponowne rozwiązanie DNS przez klienta HTTP nie może podmienić celu (DNS rebinding);
- przekierowania obsługujemy sami i każde sprawdzamy tak samo (najwyżej `MAX_REDIRECTS`);
- limit czasu całej operacji i limit rozmiaru treści (liczony w trakcie czytania);
- bez proxy ze zmiennych środowiskowych i bez ciasteczek.
"""

import asyncio
import ipaddress
import re
import socket
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import httpx

TIMEOUT_SECONDS = 10.0
MAX_BYTES = 2_000_000
MAX_REDIRECTS = 5
USER_AGENT = "Kupto/2.0 (lista zakupow z przepisu)"
HTML_TYPES = {"text/html", "application/xhtml+xml"}
_DEFAULT_PORTS = {"http": 80, "https": 443}
_META_CHARSET = re.compile(rb"""<meta[^>]+charset=["']?([A-Za-z0-9_.:-]+)""", re.IGNORECASE)

Resolver = Callable[[str, int], Awaitable[list[str]]]


class FetchError(Exception):
    """Strony nie da się (bezpiecznie) pobrać; komunikat jest dla modelu i użytkownika."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class Page:
    url: str  # adres końcowy, po przekierowaniach
    html: str


async def resolve(host: str, port: int) -> list[str]:
    infos = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return list(dict.fromkeys(str(info[4][0]) for info in infos))


def is_public_address(address: str) -> bool:
    ip = ipaddress.ip_address(address.split("%", 1)[0])  # bez strefy IPv6 („fe80::1%eth0”)
    if isinstance(ip, ipaddress.IPv6Address):
        # Adresy IPv4 schowane w IPv6 (::ffff:127.0.0.1, 6to4, Teredo) sprawdzamy jako IPv4.
        embedded = ip.ipv4_mapped or ip.sixtofour or (ip.teredo[1] if ip.teredo else None)
        if embedded is not None:
            return is_public_address(str(embedded))
    return ip.is_global and not ip.is_multicast


def validate_url(raw: str) -> httpx.URL:
    try:
        url = httpx.URL(raw.strip())
    except (httpx.InvalidURL, TypeError) as exc:
        raise FetchError("Nieprawidłowy adres strony.") from exc
    if url.scheme not in _DEFAULT_PORTS:
        raise FetchError("Obsługiwane są tylko adresy http i https.")
    if not url.host:
        raise FetchError("Adres strony nie zawiera nazwy hosta.")
    if url.userinfo:
        raise FetchError("Adres strony nie może zawierać danych logowania.")
    if url.port is not None and url.port != _DEFAULT_PORTS[url.scheme]:
        raise FetchError("Obsługiwane są tylko standardowe porty http i https.")
    return url


async def _public_address(url: httpx.URL, resolver: Resolver) -> str:
    try:
        addresses = [str(ipaddress.ip_address(url.host))]
    except ValueError:
        try:
            # `raw_host` to nazwa w IDNA (ASCII), także dla domen z polskimi znakami.
            addresses = await resolver(url.raw_host.decode("ascii"), _DEFAULT_PORTS[url.scheme])
        except OSError as exc:
            raise FetchError("Nie udało się znaleźć tej strony (błąd DNS).") from exc
    if not addresses:
        raise FetchError("Nie udało się znaleźć tej strony (błąd DNS).")
    if not all(is_public_address(a) for a in addresses):
        raise FetchError("Ten adres prowadzi do sieci prywatnej lub lokalnej — nie pobieram go.")
    return addresses[0]


async def fetch_page(
    raw_url: str,
    *,
    resolver: Resolver = resolve,
    transport: httpx.AsyncBaseTransport | None = None,
    time_limit: float = TIMEOUT_SECONDS,
    max_bytes: int = MAX_BYTES,
) -> Page:
    """Pobiera stronę HTML spod publicznego adresu albo rzuca `FetchError`."""
    url = validate_url(raw_url)
    try:
        async with (
            asyncio.timeout(time_limit),
            httpx.AsyncClient(
                transport=transport,
                trust_env=False,
                follow_redirects=False,
                timeout=time_limit,
            ) as client,
        ):
            for _ in range(MAX_REDIRECTS + 1):
                address = await _public_address(url, resolver)
                request = client.build_request(
                    "GET",
                    url.copy_with(host=address),
                    headers={
                        "Host": url.netloc.decode("ascii"),
                        "User-Agent": USER_AGENT,
                        "Accept": "text/html,application/xhtml+xml",
                        # Bez kompresji, by limit rozmiaru dotyczył tego, co faktycznie czytamy.
                        "Accept-Encoding": "identity",
                    },
                    extensions={"sni_hostname": url.raw_host.decode("ascii")},
                )
                response = await client.send(request, stream=True)
                try:
                    if response.is_redirect:
                        location = response.headers.get("location", "")
                        url = validate_url(str(url.join(location)))
                        continue
                    return Page(str(url), await _read_html(response, max_bytes))
                finally:
                    await response.aclose()
            raise FetchError("Strona przekierowuje zbyt wiele razy.")
    except TimeoutError as exc:
        raise FetchError("Strona nie odpowiedziała na czas.") from exc
    except httpx.InvalidURL as exc:
        raise FetchError("Strona przekierowuje pod nieprawidłowy adres.") from exc
    except httpx.HTTPError as exc:
        raise FetchError("Nie udało się połączyć ze stroną.") from exc


async def _read_html(response: httpx.Response, max_bytes: int) -> str:
    if response.status_code != 200:
        raise FetchError(f"Strona zwróciła błąd HTTP {response.status_code}.")
    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type not in HTML_TYPES:
        raise FetchError("Pod tym adresem nie ma strony HTML.")
    declared = response.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > max_bytes:
        raise FetchError("Strona jest zbyt duża.")
    body = bytearray()
    async for chunk in response.aiter_bytes():
        body += chunk
        if len(body) > max_bytes:
            raise FetchError("Strona jest zbyt duża.")
    return bytes(body).decode(_encoding(response, bytes(body[:4096])), errors="replace")


def _encoding(response: httpx.Response, head: bytes) -> str:
    candidates = [response.charset_encoding]
    if match := _META_CHARSET.search(head):
        candidates.append(match.group(1).decode("ascii"))
    for name in candidates:
        if name:
            try:
                "".encode(name)
                return name
            except LookupError:
                continue
    return "utf-8"

"""Generowanie pary kluczy VAPID dla Web Push.

    uv run python -m kupto.push.keys

Wypisuje linie `VAPID_PUBLIC_KEY=…` i `VAPID_PRIVATE_KEY=…` (base64url bez dopełnienia, jedna
linia bez znaków specjalnych — przechodzi przez `.env` generowany z SSM). Klucz prywatny to
sekret; zmiana pary unieważnia wszystkie zapisane subskrypcje (klienci odnowią je przy otwarciu
aplikacji).
"""

import base64

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64url_decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def public_key_of(private_key: ec.EllipticCurvePrivateKey) -> str:
    """Klucz publiczny jako nieskompresowany punkt P-256 — `applicationServerKey` przeglądarki."""
    return b64url(
        private_key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    )


def generate() -> tuple[str, str]:
    """Nowa para (publiczny, prywatny); prywatny to surowe 32 bajty skalara."""
    key = ec.generate_private_key(ec.SECP256R1())
    private_raw = key.private_numbers().private_value.to_bytes(32, "big")
    return public_key_of(key), b64url(private_raw)


def main() -> None:
    public, private = generate()
    print(f"VAPID_PUBLIC_KEY={public}")
    print(f"VAPID_PRIVATE_KEY={private}")


if __name__ == "__main__":
    main()

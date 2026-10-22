"""Konfiguracja VAPID sprawdzana raz przy starcie aplikacji (design D2).

Brak kluczy albo błędna konfiguracja wyłącza powiadomienia, ale nie zatrzymuje backendu.
"""

import logging
from dataclasses import dataclass

from cryptography.hazmat.primitives.asymmetric import ec
from py_vapid import Vapid

from kupto.config import Settings
from kupto.push.keys import b64url_decode, public_key_of

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VapidConfig:
    public_key: str
    subject: str
    signer: Vapid

    @classmethod
    def from_settings(cls, settings: Settings) -> "VapidConfig | None":
        """Poprawna konfiguracja albo None (powiadomienia wyłączone — powód w logu)."""
        public = settings.vapid_public_key.strip()
        private = settings.vapid_private_key.strip()
        subject = settings.vapid_subject.strip()
        if not (public or private or subject):
            logger.info("Powiadomienia push wyłączone: brak kluczy VAPID.")
            return None
        if not (public and private and subject):
            logger.error(
                "Powiadomienia push wyłączone: VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY "
                "i VAPID_SUBJECT muszą być ustawione razem."
            )
            return None
        try:
            raw = b64url_decode(private)
            if len(raw) != 32:
                raise ValueError("klucz prywatny musi mieć 32 bajty")
            key = ec.derive_private_key(int.from_bytes(raw, "big"), ec.SECP256R1())
        except Exception:
            # Bez szczegółów wyjątku — mogłyby zawierać fragment sekretu.
            logger.error("Powiadomienia push wyłączone: nieprawidłowy VAPID_PRIVATE_KEY.")
            return None
        if public_key_of(key) != public.rstrip("="):
            logger.error(
                "Powiadomienia push wyłączone: VAPID_PUBLIC_KEY nie pasuje do VAPID_PRIVATE_KEY."
            )
            return None
        signer = Vapid(key)
        try:
            # Próbny podpis sprawdza `subject` tak samo jak przy wysyłce (mailto:… lub https://…).
            signer.sign({"sub": subject, "aud": "https://push.example"})
        except Exception:
            logger.error(
                "Powiadomienia push wyłączone: VAPID_SUBJECT musi mieć postać mailto:adres@domena "
                "albo https://domena."
            )
            return None
        return cls(public_key=public.rstrip("="), subject=subject, signer=signer)

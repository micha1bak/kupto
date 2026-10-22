"""Treść powiadomienia push (design D7)."""

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

Urgency = Literal["very-low", "low", "normal", "high"]

# Nagłówek `Topic` usługi push: najwyżej 32 znaki alfabetu base64url (RFC 8030, 5.4).
_TOPIC = re.compile(r"[A-Za-z0-9_-]{1,32}")


class NotificationType(StrEnum):
    """Rodzaje powiadomień. Wartości są stabilne — ustawienia użytkownika (#32) je zapisują."""

    SHOPPING_STARTED = "shopping_started"  # #29 „X idzie na zakupy”
    ITEMS_ADDED = "items_added"  # #30 „Dopisano w trakcie” (tylko do kupujących)
    SHOPPING_FINISHED = "shopping_finished"  # #31 „Zakupy zakończone” z brakami


@dataclass(frozen=True)
class Notification:
    type: NotificationType
    title: str
    body: str
    # Adres w aplikacji otwierany po kliknięciu, gdy żadna karta Kupto nie jest otwarta.
    url: str = "/"
    # Powiadomienia z tym samym tagiem zastępują się na urządzeniu (np. „kupto-items-added-7”).
    tag: str | None = None
    # Jak długo usługa push ma próbować doręczyć powiadomienie do urządzenia offline.
    ttl: int = 3600
    urgency: Urgency = "normal"

    def payload(self) -> str:
        """Ładunek odczytywany przez service worker (`sw.ts`, zdarzenie `push`)."""
        return json.dumps(
            {
                "type": str(self.type),
                "title": self.title,
                "body": self.body,
                "url": self.url,
                "tag": self.tag,
            },
            ensure_ascii=False,
        )

    @property
    def topic(self) -> str | None:
        """Temat dla usługi push: niedostarczone powiadomienie o tym temacie zostaje zastąpione."""
        return self.tag if self.tag and _TOPIC.fullmatch(self.tag) else None

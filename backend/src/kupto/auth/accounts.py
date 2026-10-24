"""Adresy e-mail kont i stan ich potwierdzenia (#77, design D1, D3, D4)."""

import re
from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, StringConstraints
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from kupto.auth import tokens
from kupto.db import utcnow
from kupto.models import AuthToken, User

MAX_EMAIL_LENGTH = 254

# Część lokalna: znaki dozwolone bez cudzysłowów (RFC 5322 „dot-atom”); domena: etykiety
# [a-z0-9-] z kropkami i co najmniej dwiema częściami (IDN po zamianie na punycode). Bez
# sprawdzania MX — prawdziwą walidacją jest link weryfikacyjny.
_EMAIL = re.compile(
    r"[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*"
    r"@(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
)


def normalize_email(value: str) -> str:
    return value.strip().lower()


def _validate_email(value: str) -> str:
    email = normalize_email(value)
    local, _, _ = email.partition("@")
    if len(email) > MAX_EMAIL_LENGTH or len(local) > 64 or not _EMAIL.fullmatch(email):
        raise ValueError("Podaj poprawny adres e-mail.")
    return email


# Adres w danych wejściowych: obcięty ze spacji, małymi literami, poprawny składniowo.
Email = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=MAX_EMAIL_LENGTH + 10),
    AfterValidator(_validate_email),
]


async def find_by_identifier(
    session: AsyncSession, identifier: str, *, verified_only: bool = False
) -> User | None:
    """Konto po adresie (bez względu na wielkość liter) albo — w koncie bez adresu — po loginie.

    Login działa tylko, dopóki konto nie ma adresu w `users.email` (design D4). Przy trafieniu
    w oba (login jednego konta równy adresowi innego) wygrywa adres. `verified_only` pomija
    konta z niepotwierdzonym adresem (dodawanie domownika, D9).
    """
    identifier = identifier.strip()
    if not identifier:
        return None
    by_email = func.lower(User.email) == identifier.lower()
    if verified_only:
        by_email = by_email & User.email_verified_at.is_not(None)
    by_login = (User.login == identifier) & User.email.is_(None)
    return await session.scalar(
        select(User).where(or_(by_email, by_login)).order_by(by_email.desc(), User.id).limit(1)
    )


async def email_taken(session: AsyncSession, email: str, *, by_other_than: User) -> bool:
    return (
        await session.scalar(
            select(User.id).where(
                func.lower(User.email) == email.lower(), User.id != by_other_than.id
            )
        )
        is not None
    )


async def pending_email(session: AsyncSession, user: User) -> str | None:
    """Adres z ostatniego niewykorzystanego linku weryfikacyjnego (także wygasłego)."""
    return await session.scalar(
        select(AuthToken.email)
        .where(
            AuthToken.user_id == user.id,
            AuthToken.purpose == tokens.VERIFY_EMAIL,
            AuthToken.used_at.is_(None),
        )
        .order_by(AuthToken.created_at.desc(), AuthToken.id.desc())
        .limit(1)
    )


EmailStatus = Literal["verified", "unverified", "missing"]


def email_status(user: User) -> EmailStatus:
    if user.email_verified_at is not None:
        return "verified"
    # Konto sprzed #77 dostaje termin dopiero po podaniu adresu (D4).
    return "unverified" if user.verify_email_by is not None else "missing"


def is_blocked(user: User, mail_enabled: bool, now: datetime | None = None) -> bool:
    """Czy funkcje gospodarstwa są zablokowane do potwierdzenia adresu (D3, D4, D8)."""
    if not mail_enabled or user.email_verified_at is not None:
        return False
    return user.verify_email_by is None or (now or utcnow()) >= user.verify_email_by

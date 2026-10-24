"""Treść maili z linkami (#77). Token we fragmencie adresu (`#token=`) — przeglądarka nie
wysyła go do serwera, więc nie trafia do logów proxy ani do nagłówka `Referer` (design D2)."""

from kupto.config import Settings
from kupto.mail import EmailMessage


def verification_message(
    settings: Settings, to: str, token: str, name: str, *, has_login: bool
) -> EmailMessage:
    link = f"{settings.app_url}/verify-email#token={token}"
    hours = settings.email_verification_ttl_hours
    login_note = (
        "\nPo potwierdzeniu logujesz się tym adresem e-mail zamiast dotychczasowego loginu.\n"
        if has_login
        else ""
    )
    body = (
        f"Cześć {name},\n\n"
        "potwierdź swój adres e-mail w Kupto, otwierając link:\n\n"
        f"{link}\n\n"
        f"Link jest ważny przez {hours} godz. i działa tylko raz.\n"
        f"{login_note}\n"
        "Jeśli to nie Ty zakładałeś konto w Kupto, zignoruj tę wiadomość.\n"
    )
    return EmailMessage(
        to=to, subject="Potwierdź adres e-mail w Kupto", body=body, kind="verify_email"
    )


def password_reset_message(settings: Settings, to: str, token: str, name: str) -> EmailMessage:
    link = f"{settings.app_url}/reset-password#token={token}"
    minutes = settings.password_reset_ttl_minutes
    body = (
        f"Cześć {name},\n\n"
        "ktoś (pewnie Ty) poprosił o ustawienie nowego hasła do Kupto. Otwórz link:\n\n"
        f"{link}\n\n"
        f"Link jest ważny przez {minutes} min i działa tylko raz. Po zmianie hasła wylogujemy "
        "Cię na wszystkich urządzeniach.\n\n"
        "Jeśli to nie Ty, zignoruj tę wiadomość — hasło się nie zmieni.\n"
    )
    return EmailMessage(to=to, subject="Nowe hasło do Kupto", body=body, kind="reset_password")

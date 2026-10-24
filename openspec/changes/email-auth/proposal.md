# Proposal

## Why

Konto w Kupto to dziś login i hasło. Login nie pozwala odzyskać dostępu po zapomnieniu hasła (nie ma dokąd wysłać linku), a do tego jest pokazywany domownikom w kilku widokach (lista, historia, przepisy, plan obiadów, domownicy). #77 zastępuje login adresem e-mail z weryfikacją i dodaje „Zapomniałem hasła”. Imię (#78) jest już wymagane, więc w UI login może zniknąć na rzecz imienia.

## What Changes

- **Rejestracja e-mailem**: `POST /api/auth/register` przyjmuje `email` (walidowany, unikalny bez względu na wielkość liter, zapisywany małymi literami), hasło i imię — bez loginu. Na adres wysyłany jest link weryfikacyjny.
- **Weryfikacja adresu**: jednorazowy token (w bazie tylko skrót SHA-256) ważny 48 h; strona `/verify-email#token=…` potwierdza adres (`POST /api/auth/verify-email`). Konto niezweryfikowane działa normalnie przez 7 dni z banerem „Potwierdź adres e-mail”; po terminie aplikacja jest zablokowana (ekran z ponownym wysłaniem linku), a backend odrzuca żądania gospodarstwa kodem 403 `email_unverified` (D3).
- **Logowanie e-mailem**: `POST /api/auth/login` przyjmuje `email` i hasło. Konta sprzed zmiany logują się loginem, dopóki nie potwierdzą adresu; potem tylko e-mailem (D4). Stare klienty wysyłające pole `login` działają dalej.
- **Istniejące konta**: po zalogowaniu loginem blokujący ekran „Podaj adres e-mail” (`POST /api/users/me/email`) — potem 7 dni na kliknięcie linku, jak przy nowym koncie.
- **„Zapomniałem hasła”**: `POST /api/auth/password-reset` zawsze odpowiada tak samo (nie zdradza, czy konto istnieje); link `/reset-password#token=…` ważny 30 min, jednorazowy; `POST /api/auth/password-reset/confirm` ustawia nowe hasło, unieważnia token i wszystkie wcześniejsze sesje JWT konta (D6).
- **Limity prób** (tabela `auth_rate_events`): rejestracja z jednego IP, prośby o reset (na adres i na IP), wysyłka linku weryfikacyjnego (na konto i na adres) — 429 z `Retry-After`.
- **Wysyłka maili**: abstrakcja `MailSender` z backendem `log` (domyślny; bez wysyłki, link w logu tylko przy `MAIL_LOG_LINKS=true` w dev) i `ses` (Amazon SES v2 przez boto3, eu-north-1, poświadczenia z roli instancji). Dopóki produkcja ma `log`, wysyłka jest „niedostępna”: weryfikacja nie jest wymagana, nikt nie jest blokowany, a „Zapomniałem hasła” pokazuje komunikat o niedostępności (D7, D8).
- **Imiona zamiast loginów**: lista (zapotrzebowania, kupione przez, robi zakupy), historia, przepisy, plan obiadów, preferencje i domownicy pokazują imię (`display_name`); login ani e-mail nie trafiają do domowników. Pola API `login` w zapotrzebowaniach, kupujących i członkach zmieniają nazwę na `name`.
- **Dodawanie domownika** po adresie e-mail (potwierdzonym, gdy wysyłka działa) albo — dla kont bez adresu — po loginie.
- **Infra**: tożsamość domenowa SES `kupto.bakweb.pl` z Easy DKIM i MAIL FROM, uprawnienie `ses:SendEmail` dla roli EC2, `http_put_response_hop_limit = 2` (kontener backendu musi sięgnąć po poświadczenia roli), outputy z rekordami DNS do ręcznego dodania w SEOHOST. `terraform apply`, DNS i wyjście z sandboxa SES wykonuje właściciel.

## Capabilities

### New Capabilities

_(brak)_

### Modified Capabilities

- `user-accounts`: rejestracja i logowanie e-mailem, weryfikacja adresu, adres w istniejących kontach, reset hasła, limity prób, wysyłka maili niedostępna, prywatność loginu i adresu.
- `households`: dodawanie członka po adresie e-mail; lista członków z imionami zamiast loginów.

## Impact

- **Backend**: `models.py` (`User.email`, `email_verified_at`, `verify_email_by`, `sessions_valid_after`, `login` opcjonalny; `AuthToken`, `AuthRateEvent`), migracja `0013`, nowe `kupto/auth/{accounts,tokens,rate_limit}.py` i `kupto/mail/`, `auth/router.py`, `deps.py` (sesje sprzed resetu, blokada niezweryfikowanych), `households/` (dodawanie po e-mailu, imiona), schematy listy, historii, przepisów, planu obiadów i preferencji (imiona), `config.py` (`MAIL_*`, `KUPTO_DOMAIN`, terminy), zależność `boto3`.
- **Frontend**: `AuthForm` (e-mail), nowe strony `/forgot-password`, `/reset-password`, `/verify-email`, ekran „Podaj adres e-mail”, baner i blokada weryfikacji, sekcja adresu na profilu, imiona w liście, historii i u domowników, dodawanie domownika po e-mailu.
- **API**: zmiana kształtu `POST /api/auth/register` (`email` zamiast `login`), pola `name` zamiast `login` w liście i u domowników, nowe pola profilu; nowe endpointy weryfikacji i resetu.
- **Infra/deploy**: `infra/ses.tf`, `iam.tf`, `main.tf` (hop limit), outputy; `deploy/docker-compose.yml` (`MAIL_*`, `KUPTO_DOMAIN`, `AWS_REGION`); nowe parametry SSM opisane w `infra/README.md`.
- **Poza zakresem**: zmiana potwierdzonego adresu (wymaga ponownego podania hasła), unieważnianie sesji „wyloguj wszędzie” (#54), limit prób logowania, zaproszenia do gospodarstwa.

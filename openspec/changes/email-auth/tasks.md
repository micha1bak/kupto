# Tasks

## 1. Model danych (D1)

- [x] 1.1 `User.email`, `email_verified_at`, `verify_email_by`, `sessions_valid_after`, `login` opcjonalny; `AuthToken`, `AuthRateEvent`; migracja `0013` z `down_revision = "0012"`
- [x] 1.2 `tests/test_migrations.py`: upgrade z 0012 na danych (istniejące konta bez zmian, unikalność adresu bez względu na wielkość liter), downgrade z kontem bez loginu, ponowny upgrade

## 2. Wysyłka maili (D7, D8)

- [x] 2.1 `kupto.mail`: `MailSender`, `LogMailSender` (link w logu tylko z `MAIL_LOG_LINKS`), `SesMailSender` (boto3 SESv2), wybór z konfiguracji z bezpiecznym powrotem do `log`; treść maili weryfikacji i resetu; testy (brak tokenu w logu, wywołanie SESv2 na atrapie)
- [x] 2.2 Konfiguracja `MAIL_BACKEND`, `MAIL_FROM`, `MAIL_SES_REGION`, `MAIL_LOG_LINKS`, `KUPTO_DOMAIN`, terminy; `backend/README.md`, `.env.example`, `deploy/docker-compose.yml`, `docker-compose.yml`

## 3. Konta (spec: user-accounts)

- [x] 3.1 Tokeny jednorazowe (D2) i limity prób (D5)
- [x] 3.2 Rejestracja i logowanie e-mailem, logowanie loginem do potwierdzenia adresu (D4), profil (D10); testy API
- [x] 3.3 Weryfikacja adresu i podanie adresu w istniejącym koncie, termin i blokada `email_unverified` / `email_required` (D3, D4); testy (ważny, wygasły, użyty token; blokada po terminie; brak blokady bez wysyłki)
- [x] 3.4 Reset hasła: prośba bez zdradzania istnienia konta, potwierdzenie, unieważnienie sesji (D6); testy
- [x] 3.5 Testy limitów prób

## 4. Imiona i domownicy (spec: households, D9)

- [x] 4.1 `display_name` w liście, historii, przepisach, planie obiadów, preferencjach; pola `name` zamiast `login`; testy
- [x] 4.2 Dodawanie domownika po adresie e-mail (alias `login`); testy

## 5. Frontend

- [x] 5.1 `AuthForm` z adresem e-mail, strony `/forgot-password`, `/reset-password`, `/verify-email`; testy Vitest
- [x] 5.2 Ekran „Podaj adres e-mail”, baner i blokada weryfikacji, adres na profilu; testy
- [x] 5.3 Imiona w liście, historii, u domowników; dodawanie domownika po adresie; testy

## 6. Infra (D7)

- [x] 6.1 `infra/ses.tf`: tożsamość domeny z DKIM i MAIL FROM, `ses:SendEmail` dla roli, hop limit IMDS 2, outputy z rekordami DNS; `terraform fmt` i `validate`
- [x] 6.2 `infra/README.md` i `deploy/README.md`: apply, rekordy DNS w SEOHOST, wyjście z sandboxa SES, parametry SSM

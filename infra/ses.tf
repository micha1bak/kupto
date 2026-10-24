# Wysyłka maili aplikacji (#77): linki weryfikacji adresu i resetu hasła przez Amazon SES.
# DNS domeny jest w SEOHOST (poza AWS), więc rekordy z outputu `ses_dns_records` dodaje się
# ręcznie (infra/README.md). Do czasu weryfikacji domeny i wyjścia z sandboxa SES aplikacja
# działa z MAIL_BACKEND=log (bez wysyłki).

variable "mail_domain" {
  description = "Domena nadawcy maili aplikacji (tożsamość SES z DKIM), np. adres no-reply@<domena>."
  type        = string
  default     = "kupto.bakweb.pl"
}

resource "aws_sesv2_email_identity" "app" {
  email_identity = var.mail_domain

  # Easy DKIM: SES generuje klucze i podpisuje maile; potrzebne 3 rekordy CNAME.
  dkim_signing_attributes {
    next_signing_key_length = "RSA_2048_BIT"
  }
}

# Własna domena MAIL FROM (Return-Path) — SPF wyrównany z domeną nadawcy (DMARC).
resource "aws_sesv2_email_identity_mail_from_attributes" "app" {
  email_identity         = aws_sesv2_email_identity.app.email_identity
  mail_from_domain       = "mail.${var.mail_domain}"
  behavior_on_mx_failure = "USE_DEFAULT_VALUE"
}

locals {
  ses_dns_records = concat(
    [
      for token in aws_sesv2_email_identity.app.dkim_signing_attributes[0].tokens : {
        type  = "CNAME"
        name  = "${token}._domainkey.${var.mail_domain}"
        value = "${token}.dkim.amazonses.com"
      }
    ],
    [
      {
        type  = "MX"
        name  = "mail.${var.mail_domain}"
        value = "10 feedback-smtp.${var.aws_region}.amazonses.com"
      },
      {
        type  = "TXT"
        name  = "mail.${var.mail_domain}"
        value = "v=spf1 include:amazonses.com ~all"
      },
      {
        # Najpierw tylko raporty (p=none); po kilku tygodniach bez problemów — p=quarantine.
        type  = "TXT"
        name  = "_dmarc.${var.mail_domain}"
        value = "v=DMARC1; p=none"
      },
    ],
  )
}

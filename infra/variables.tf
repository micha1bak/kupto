variable "aws_profile" {
  description = "Profil AWS CLI projektu kupto (aws login --profile kupto)."
  type        = string
  default     = "kupto"
}

variable "aws_region" {
  description = "Region przydzielony projektowi kupto w nowym interfejsie AWS."
  type        = string
  default     = "eu-north-1"
}

variable "instance_type" {
  description = "Typ instancji; t4g.small, gdyby 1 GiB pamięci nie wystarczał."
  type        = string
  default     = "t4g.micro"
}

variable "root_volume_size" {
  description = "Rozmiar dysku systemowego w GB (system, obrazy Dockera, dane Postgresa)."
  type        = number
  default     = 20
}

variable "compose_version" {
  description = "Wersja wtyczki Docker Compose instalowanej przy pierwszym starcie."
  type        = string
  default     = "v5.6.0"
}

variable "backup_retention_days" {
  description = "Po ilu dniach usuwać zrzuty bazy z bucketu kopii."
  type        = number
  default     = 35
}

variable "volume_backup_retention_days" {
  description = "Po ilu dniach AWS Backup usuwa cotygodniowe kopie dysku serwera."
  type        = number
  default     = 28
}

variable "budget_email" {
  description = "Adres powiadomień budżetu i alarmów. Bez wartości domyślnej i poza repo: TF_VAR_budget_email lub -var (zob. README)."
  type        = string
  nullable    = false

  validation {
    condition     = can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", var.budget_email))
    error_message = "budget_email musi być adresem e-mail."
  }
}

variable "monthly_budget_usd" {
  description = "Miesięczny budżet kosztów AWS w USD (powiadomienia: 80% prognozy, 100% faktycznych)."
  type        = number
  default     = 15
}

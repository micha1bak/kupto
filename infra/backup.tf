# Cotygodniowe kopie dysku serwera przez AWS Backup (#22; Data Lifecycle Manager nie jest
# dostępny w projektach). Uzupełniają codzienne zrzuty bazy do S3 (deploy/kupto-backup.sh):
# zrzut odtwarza dane, kopia wolumenu — cały serwer (system, .env, certyfikaty Caddy).

resource "aws_backup_vault" "kupto" {
  name = "kupto"
}

resource "aws_backup_plan" "weekly" {
  name = "kupto-weekly"

  rule {
    rule_name         = "weekly"
    target_vault_name = aws_backup_vault.kupto.name
    # Niedziela 02:00 UTC — przed codziennym zrzutem bazy (03:00) i poza godzinami użycia.
    schedule          = "cron(0 2 ? * SUN *)"
    start_window      = 60
    completion_window = 360

    lifecycle {
      delete_after = var.volume_backup_retention_days
    }
  }
}

# Wolumeny EBS z tagiem Backup = weekly (dysk systemowy serwera, infra/main.tf).
resource "aws_backup_selection" "weekly" {
  name         = "kupto-weekly-volumes"
  plan_id      = aws_backup_plan.weekly.id
  iam_role_arn = aws_iam_role.backup.arn
  resources    = ["arn:aws:ec2:${var.aws_region}:${data.aws_caller_identity.current.account_id}:volume/*"]

  condition {
    string_equals {
      key   = "aws:ResourceTag/Backup"
      value = "weekly"
    }
  }
}

data "aws_iam_policy_document" "backup_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["backup.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_iam_role" "backup" {
  name               = "kupto-backup"
  assume_role_policy = data.aws_iam_policy_document.backup_assume.json
}

resource "aws_iam_role_policy_attachment" "backup" {
  for_each = toset([
    "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup",
    "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForRestores",
  ])

  role       = aws_iam_role.backup.name
  policy_arn = each.value
}

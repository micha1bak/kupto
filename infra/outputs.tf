output "public_ip" {
  description = "Stały adres serwera — na niego wskazuje rekord A subdomeny (#19)."
  value       = aws_eip.app.public_ip
}

output "instance_id" {
  value = aws_instance.app.id
}

output "backup_bucket" {
  value = aws_s3_bucket.backups.bucket
}

output "session_command" {
  description = "Powłoka na serwerze przez Session Manager (wymaga wtyczki session-manager-plugin)."
  value       = "aws ssm start-session --profile ${var.aws_profile} --target ${aws_instance.app.id}"
}

output "ses_dns_records" {
  description = "Rekordy DNS do ręcznego dodania w SEOHOST: DKIM (CNAME), MAIL FROM (MX, SPF) i DMARC (#77)."
  value       = local.ses_dns_records
}

output "ses_identity_status" {
  description = "Sprawdzenie weryfikacji domeny w SES po dodaniu rekordów DNS."
  value       = "aws sesv2 get-email-identity --profile ${var.aws_profile} --email-identity ${var.mail_domain} --query '{verified: VerifiedForSendingStatus, dkim: DkimAttributes.Status, mail_from: MailFromAttributes.MailFromDomainStatus}'"
}

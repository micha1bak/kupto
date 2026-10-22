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

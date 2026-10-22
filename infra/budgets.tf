# Kontrola kosztów i proste alarmy działania (#23). Powiadomienia idą na adres z
# var.budget_email — podawany przy plan/apply, nigdy zapisywany w repo (zob. README).

resource "aws_budgets_budget" "monthly" {
  name         = "kupto-miesiecznie"
  budget_type  = "COST"
  limit_amount = format("%.2f", var.monthly_budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  # Koszt przed odjęciem kredytów: plan Free płaci kredytami, więc koszt netto byłby zerowy
  # aż do ich wyczerpania, a budżet ma ostrzegać o tempie zużycia.
  cost_types {
    include_credit = false
    include_refund = false
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.budget_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.budget_email]
  }
}

# Alarmy CloudWatch → SNS → e-mail. Subskrypcję trzeba potwierdzić linkiem z wiadomości od AWS.
resource "aws_sns_topic" "alerts" {
  name = "kupto-alerts"
}

resource "aws_sns_topic_subscription" "alerts_email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.budget_email
}

# Serwer nie przechodzi kontroli stanu (system AWS lub sama instancja) przez 5 minut.
resource "aws_cloudwatch_metric_alarm" "status_check" {
  alarm_name          = "kupto-status-check-failed"
  alarm_description   = "Instancja kupto nie przechodzi kontroli stanu EC2 - aplikacja prawdopodobnie nie dziala."
  namespace           = "AWS/EC2"
  metric_name         = "StatusCheckFailed"
  dimensions          = { InstanceId = aws_instance.app.id }
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 5
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  # Brak danych (np. zatrzymana instancja) też jest awarią.
  treat_missing_data = "breaching"
  alarm_actions      = [aws_sns_topic.alerts.arn]
  ok_actions         = [aws_sns_topic.alerts.arn]
}

# Instancje t4g działają domyślnie w trybie „unlimited”: długie obciążenie CPU ponad bazowy
# poziom jest dodatkowo płatne. Alarm przy pierwszych naliczonych kredytach nadwyżkowych.
resource "aws_cloudwatch_metric_alarm" "cpu_surplus_charged" {
  alarm_name          = "kupto-cpu-surplus-charged"
  alarm_description   = "Instancja kupto zuzywa platne kredyty CPU ponad bazowy poziom (t4g unlimited)."
  namespace           = "AWS/EC2"
  metric_name         = "CPUSurplusCreditsCharged"
  dimensions          = { InstanceId = aws_instance.app.id }
  statistic           = "Sum"
  period              = 3600
  evaluation_periods  = 1
  comparison_operator = "GreaterThanThreshold"
  threshold           = 0
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}

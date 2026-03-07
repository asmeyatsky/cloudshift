# --- CloudWatch Log Groups ---

resource "aws_cloudwatch_log_group" "lambda_api" {
  name              = "/aws/lambda/${aws_lambda_function.api_handler.function_name}"
  retention_in_days = 30

  tags = { Component = "monitoring" }
}

resource "aws_cloudwatch_log_group" "lambda_processor" {
  name              = "/aws/lambda/${aws_lambda_function.stream_processor.function_name}"
  retention_in_days = 30

  tags = { Component = "monitoring" }
}

resource "aws_cloudwatch_log_group" "ecs_backend" {
  name              = "/ecs/${local.name_prefix}-backend"
  retention_in_days = 14

  tags = { Component = "monitoring" }
}

# --- CloudWatch Alarms ---

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${local.name_prefix}-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Lambda error rate exceeds threshold"
  alarm_actions       = [aws_sns_topic.notifications.arn]

  dimensions = {
    FunctionName = aws_lambda_function.api_handler.function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  alarm_name          = "${local.name_prefix}-dlq-messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Messages appearing in DLQ"
  alarm_actions       = [aws_sns_topic.notifications.arn]

  dimensions = {
    QueueName = aws_sqs_queue.processing_dlq.name
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  alarm_name          = "${local.name_prefix}-rds-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "RDS CPU utilization high"
  alarm_actions       = [aws_sns_topic.notifications.arn]

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.postgres.identifier
  }
}

# --- CloudWatch Dashboard ---

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${local.name_prefix}-overview"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", aws_lambda_function.api_handler.function_name],
            ["AWS/Lambda", "Errors", "FunctionName", aws_lambda_function.api_handler.function_name]
          ]
          period = 300
          region = var.aws_region
          title  = "Lambda API Handler"
        }
      }
    ]
  })
}

# --- SQS Processing Queue with DLQ ---

resource "aws_sqs_queue" "processing" {
  name                       = "${local.name_prefix}-processing"
  visibility_timeout_seconds = 120
  message_retention_seconds  = 345600
  receive_wait_time_seconds  = 10
  delay_seconds              = 0

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.processing_dlq.arn
    maxReceiveCount     = 3
  })

  tags = { Component = "messaging" }
}

resource "aws_sqs_queue" "processing_dlq" {
  name                      = "${local.name_prefix}-processing-dlq"
  message_retention_seconds = 1209600

  tags = { Component = "messaging" }
}

resource "aws_sqs_queue_redrive_allow_policy" "processing_dlq" {
  queue_url = aws_sqs_queue.processing_dlq.id

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns   = [aws_sqs_queue.processing.arn]
  })
}

# --- SNS Notifications Topic ---

resource "aws_sns_topic" "notifications" {
  name              = "${local.name_prefix}-notifications"
  kms_master_key_id = aws_kms_key.main.id

  tags = { Component = "messaging" }
}

resource "aws_sns_topic_subscription" "email_alerts" {
  topic_arn = aws_sns_topic.notifications.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_sns_topic_subscription" "sqs_fanout" {
  topic_arn = aws_sns_topic.notifications.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.processing.arn
}

# --- EventBridge Scheduled Rule ---

resource "aws_cloudwatch_event_rule" "daily_cleanup" {
  name                = "${local.name_prefix}-daily-cleanup"
  description         = "Triggers daily data cleanup Lambda"
  schedule_expression = "cron(0 2 * * ? *)"

  tags = { Component = "scheduling" }
}

resource "aws_cloudwatch_event_target" "cleanup_lambda" {
  rule = aws_cloudwatch_event_rule.daily_cleanup.name
  arn  = aws_lambda_function.stream_processor.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.stream_processor.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_cleanup.arn
}

# --- KMS Key ---

resource "aws_kms_key" "main" {
  description             = "Main encryption key for ${local.project_name}"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EnableRootAccountAccess"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "AllowLambdaUsage"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.lambda_exec.arn
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = { Component = "security" }
}

resource "aws_kms_alias" "main" {
  name          = "alias/${local.name_prefix}-main"
  target_key_id = aws_kms_key.main.key_id
}

# --- Secrets Manager ---

resource "aws_secretsmanager_secret" "db_password" {
  name        = "${local.name_prefix}/db-password"
  description = "Database master password"
  kms_key_id  = aws_kms_key.main.arn

  tags = { Component = "security" }
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = var.db_password
}

resource "aws_secretsmanager_secret" "api_keys" {
  name        = "${local.name_prefix}/api-keys"
  description = "Third-party API keys"
  kms_key_id  = aws_kms_key.main.arn

  tags = { Component = "security" }
}

resource "aws_secretsmanager_secret_version" "api_keys" {
  secret_id = aws_secretsmanager_secret.api_keys.id
  secret_string = jsonencode({
    stripe_key   = var.stripe_api_key
    sendgrid_key = var.sendgrid_api_key
  })
}

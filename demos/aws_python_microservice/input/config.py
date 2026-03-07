"""AWS-specific configuration for the microservice."""

import os

# AWS Region and Account
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
AWS_ACCOUNT_ID = os.environ.get("AWS_ACCOUNT_ID", "123456789012")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")

# S3 Configuration
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "myapp-data-bucket")
S3_UPLOAD_PREFIX = "uploads/"
S3_PRESIGNED_URL_EXPIRY = 3600  # seconds

# DynamoDB Configuration
DYNAMODB_TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME", "myapp-items")
DYNAMODB_GSI_NAME = "status-created-index"

# SQS Configuration
SQS_QUEUE_URL = os.environ.get(
    "SQS_QUEUE_URL",
    f"https://sqs.{AWS_REGION}.amazonaws.com/{AWS_ACCOUNT_ID}/myapp-tasks",
)
SQS_DLQ_URL = os.environ.get(
    "SQS_DLQ_URL",
    f"https://sqs.{AWS_REGION}.amazonaws.com/{AWS_ACCOUNT_ID}/myapp-tasks-dlq",
)

# SNS Configuration
SNS_TOPIC_ARN = os.environ.get(
    "SNS_TOPIC_ARN",
    f"arn:aws:sns:{AWS_REGION}:{AWS_ACCOUNT_ID}:myapp-notifications",
)

# Secrets Manager
SECRET_NAME = os.environ.get("SECRET_NAME", "myapp/api-keys")

# IAM Role ARN for cross-account access
ASSUME_ROLE_ARN = os.environ.get(
    "ASSUME_ROLE_ARN",
    f"arn:aws:iam::{AWS_ACCOUNT_ID}:role/myapp-cross-account-role",
)

# CloudWatch
CLOUDWATCH_LOG_GROUP = f"/aws/myapp/{os.environ.get('ENV', 'dev')}"
CLOUDWATCH_NAMESPACE = "MyApp/Metrics"

# Parameter Store prefix
SSM_PARAMETER_PREFIX = f"/myapp/{os.environ.get('ENV', 'dev')}"

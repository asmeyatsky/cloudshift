output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "api_gateway_url" {
  description = "API Gateway invoke URL"
  value       = aws_api_gateway_rest_api.main.id
}

output "cloudfront_domain" {
  description = "CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.cdn.domain_name
}

output "lambda_api_function_name" {
  description = "API handler Lambda function name"
  value       = aws_lambda_function.api_handler.function_name
}

output "dynamodb_table_name" {
  description = "DynamoDB table name"
  value       = aws_dynamodb_table.main.name
}

output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.postgres.endpoint
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = aws_elasticache_cluster.redis.cache_nodes[0].address
}

output "sqs_queue_url" {
  description = "SQS processing queue URL"
  value       = aws_sqs_queue.processing.url
}

output "sns_topic_arn" {
  description = "SNS notifications topic ARN"
  value       = aws_sns_topic.notifications.arn
}

output "s3_data_bucket" {
  description = "Data S3 bucket name"
  value       = aws_s3_bucket.data.id
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "route53_zone_id" {
  description = "Route53 hosted zone ID"
  value       = aws_route53_zone.main.zone_id
}

output "kms_key_arn" {
  description = "KMS key ARN"
  value       = aws_kms_key.main.arn
}

output "bastion_public_ip" {
  description = "Bastion host public IP"
  value       = aws_instance.bastion.public_ip
}

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment (dev, staging, production)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be dev, staging, or production."
  }
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "domain_name" {
  description = "Root domain name"
  type        = string
  default     = "example.cloudshift.io"
}

variable "alert_email" {
  description = "Email address for alert notifications"
  type        = string
  default     = "alerts@cloudshift.io"
}

variable "db_password" {
  description = "Database master password"
  type        = string
  sensitive   = true
}

variable "stripe_api_key" {
  description = "Stripe API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "sendgrid_api_key" {
  description = "SendGrid API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "ecs_desired_count" {
  description = "Desired count for ECS service"
  type        = number
  default     = 2
}

variable "ssh_key_name" {
  description = "EC2 SSH key pair name"
  type        = string
  default     = "bastion-key"
}

variable "allowed_ssh_cidrs" {
  description = "CIDR blocks allowed for SSH access"
  type        = list(string)
  default     = ["10.0.0.0/8"]
}

variable "cors_allowed_origins" {
  description = "Allowed origins for CORS"
  type        = list(string)
  default     = ["https://app.cloudshift.io"]
}

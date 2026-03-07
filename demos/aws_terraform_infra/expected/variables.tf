variable "gcp_project_id" {
  description = "GCP project ID"
  type        = string
}

variable "gcp_region" {
  description = "GCP region for all resources"
  type        = string
  default     = "us-central1"
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

variable "cloudsql_tier" {
  description = "Cloud SQL instance tier"
  type        = string
  default     = "db-custom-2-8192"
}

variable "cloud_run_max_instances" {
  description = "Max instances for Cloud Run service"
  type        = number
  default     = 10
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

variable "notification_push_endpoint" {
  description = "Push endpoint for notification subscription"
  type        = string
  default     = "https://notifications.cloudshift.io/webhook"
}

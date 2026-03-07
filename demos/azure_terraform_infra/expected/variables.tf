variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "sql_admin_password" {
  description = "Cloud SQL admin password"
  type        = string
  sensitive   = true
}

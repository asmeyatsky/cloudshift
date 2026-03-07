terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    bucket = "mycompany-terraform-state"
    prefix = "infra/terraform.tfstate"
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region

  default_labels = local.common_labels
}

locals {
  project_name = "cloudshift-demo"
  environment  = var.environment
  common_labels = {
    project     = local.project_name
    environment = local.environment
    managed-by  = "terraform"
    team        = "platform-engineering"
  }
  name_prefix = "${local.project_name}-${local.environment}"
}

data "google_project" "current" {}

data "google_compute_zones" "available" {
  region = var.gcp_region
  status = "UP"
}

data "google_compute_image" "debian" {
  family  = "debian-12"
  project = "debian-cloud"
}

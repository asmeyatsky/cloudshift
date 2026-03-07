# --- Primary Data Bucket ---

resource "google_storage_bucket" "data" {
  name     = "${local.name_prefix}-data-${data.google_project.current.number}"
  location = var.gcp_region

  versioning {
    enabled = true
  }

  encryption {
    default_kms_key_name = google_kms_crypto_key.main.id
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  lifecycle_rule {
    condition {
      age = 180
    }
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }

  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type = "Delete"
    }
  }

  uniform_bucket_level_access = true

  labels = { component = "storage" }
}

# --- Static Assets Bucket ---

resource "google_storage_bucket" "assets" {
  name     = "${local.name_prefix}-assets"
  location = var.gcp_region

  versioning {
    enabled = true
  }

  cors {
    origin          = var.cors_allowed_origins
    method          = ["GET", "HEAD"]
    response_header = ["*"]
    max_age_seconds = 3600
  }

  uniform_bucket_level_access = true

  labels = { component = "cdn" }
}

# --- Artifacts Bucket ---

resource "google_storage_bucket" "artifacts" {
  name     = "${local.name_prefix}-artifacts"
  location = var.gcp_region

  uniform_bucket_level_access = true

  labels = { component = "build" }
}

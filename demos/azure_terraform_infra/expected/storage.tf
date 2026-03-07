resource "google_storage_bucket" "main" {
  name     = "myappstorageaccount"
  location = var.region

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 30
      with_state = "ARCHIVED"
    }
  }

  labels = {
    environment = "production"
  }

  uniform_bucket_level_access = true
}

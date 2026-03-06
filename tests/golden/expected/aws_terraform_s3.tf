provider "google" {
  project = var.project_id
  region  = "us-central1"
}

resource "google_storage_bucket" "data_bucket" {
  name     = "my-app-data"
  location = "US"

  labels = {
    environment = "production"
    team        = "platform"
  }

  versioning {
    enabled = true
  }

  encryption {
    default_kms_key_name = google_kms_crypto_key.default.id
  }
}

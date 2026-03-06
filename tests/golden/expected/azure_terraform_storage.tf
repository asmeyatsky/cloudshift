resource "google_storage_bucket" "example" {
  name     = "examplestorageacct"
  location = "US"

  labels = {
    environment = "production"
  }

  versioning {
    enabled = true
  }

  uniform_bucket_level_access = true
}

resource "google_cloudfunctions2_function" "processor" {
  name     = "data-processor"
  location = var.region

  build_config {
    runtime     = "python313"
    entry_point = "handler"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_source.name
        object = "lambda.zip"
      }
    }
  }

  service_config {
    available_memory   = "256Mi"
    timeout_seconds    = 30
    max_instance_count = 100

    environment_variables = {
      TABLE_NAME = google_firestore_database.events.name
      BUCKET     = google_storage_bucket.data.name
    }
  }

  labels = {
    environment = "production"
  }
}

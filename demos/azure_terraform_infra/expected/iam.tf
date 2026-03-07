resource "google_service_account" "main" {
  account_id   = "myapp-identity"
  display_name = "myapp-identity"
}

resource "google_storage_bucket_iam_member" "storage_reader" {
  bucket = google_storage_bucket.main.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.main.email}"
}

resource "google_project_iam_member" "firestore_reader" {
  project = var.project_id
  role    = "roles/datastore.viewer"
  member  = "serviceAccount:${google_service_account.main.email}"
}

resource "google_pubsub_topic_iam_member" "pubsub_publisher" {
  topic  = google_pubsub_topic.orders.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_service_account.main.email}"
}

resource "google_secret_manager_secret_iam_member" "secret_accessor" {
  secret_id = google_secret_manager_secret.main.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.main.email}"
}

resource "google_secret_manager_secret" "main" {
  secret_id = "myapp-secrets"

  replication {
    auto {}
  }
}

resource "google_firestore_database" "users" {
  name        = "users"
  location_id = "us-central1"
  type        = "FIRESTORE_NATIVE"

  labels = {
    environment = "production"
  }
}

resource "google_firestore_index" "users_email_index" {
  database   = google_firestore_database.users.name
  collection = "users"

  fields {
    field_path = "email"
    order      = "ASCENDING"
  }
}

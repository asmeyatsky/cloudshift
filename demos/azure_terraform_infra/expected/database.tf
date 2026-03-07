resource "google_firestore_database" "main" {
  name        = "myappdb"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  labels = {
    environment = "production"
  }
}

resource "google_sql_database_instance" "main" {
  name             = "myapp-sql-server"
  database_version = "SQLSERVER_2019_STANDARD"
  region           = var.region

  settings {
    tier = "db-custom-2-7680"

    ip_configuration {
      ipv4_enabled = true
    }
  }
}

resource "google_sql_database" "main" {
  name     = "myapp-db"
  instance = google_sql_database_instance.main.name
}

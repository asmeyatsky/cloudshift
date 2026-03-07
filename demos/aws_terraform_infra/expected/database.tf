# --- Firestore Database ---

resource "google_firestore_database" "main" {
  project     = var.gcp_project_id
  name        = "${local.name_prefix}-records"
  location_id = var.gcp_region
  type        = "FIRESTORE_NATIVE"

  point_in_time_recovery_enablement = "POINT_IN_TIME_RECOVERY_ENABLED"
}

resource "google_firestore_index" "gsi1" {
  project    = var.gcp_project_id
  database   = google_firestore_database.main.name
  collection = "records"

  fields {
    field_path = "gsi1pk"
    order      = "ASCENDING"
  }

  fields {
    field_path = "gsi1sk"
    order      = "ASCENDING"
  }
}

# --- Cloud SQL PostgreSQL ---

resource "google_sql_database_instance" "postgres" {
  name             = "${local.name_prefix}-postgres"
  database_version = "POSTGRES_15"
  region           = var.gcp_region

  settings {
    tier              = var.cloudsql_tier
    disk_size         = 50
    disk_autoresize   = true
    availability_type = var.environment == "production" ? "REGIONAL" : "ZONAL"

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      backup_retention_settings {
        retained_backups = 7
      }
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.main.id
    }

    database_flags {
      name  = "max_connections"
      value = "100"
    }
  }

  deletion_protection = var.environment == "production"
}

resource "google_sql_database" "appdb" {
  name     = "appdb"
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "dbadmin" {
  name     = "dbadmin"
  instance = google_sql_database_instance.postgres.name
  password = google_secret_manager_secret_version.db_password.secret_data
}

# --- Memorystore Redis ---

resource "google_redis_instance" "main" {
  name               = "${local.name_prefix}-redis"
  tier               = "BASIC"
  memory_size_gb     = 1
  region             = var.gcp_region
  redis_version      = "REDIS_7_0"
  authorized_network = google_compute_network.main.id

  labels = { component = "cache" }
}

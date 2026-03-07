# --- Cloud Functions ---

resource "google_cloudfunctions2_function" "api_handler" {
  name     = "${local.name_prefix}-api-handler"
  location = var.gcp_region

  build_config {
    runtime     = "python311"
    entry_point = "handler"
    source {
      storage_source {
        bucket = google_storage_bucket.artifacts.name
        object = "api_handler.zip"
      }
    }
  }

  service_config {
    max_instance_count    = 100
    available_memory      = "512Mi"
    timeout_seconds       = 30
    service_account_email = google_service_account.function_exec.email

    environment_variables = {
      FIRESTORE_COLLECTION = "records"
      PUBSUB_TOPIC         = google_pubsub_topic.processing.name
      ENVIRONMENT          = local.environment
    }

    vpc_connector = google_vpc_access_connector.main.id
  }

  labels = { component = "api" }
}

resource "google_cloudfunctions2_function" "stream_processor" {
  name     = "${local.name_prefix}-stream-processor"
  location = var.gcp_region

  build_config {
    runtime     = "nodejs18"
    entry_point = "handler"
    source {
      storage_source {
        bucket = google_storage_bucket.artifacts.name
        object = "stream_processor.zip"
      }
    }
  }

  service_config {
    max_instance_count    = 10
    available_memory      = "256Mi"
    timeout_seconds       = 60
    service_account_email = google_service_account.function_exec.email
  }

  labels = { component = "processing" }
}

# --- Cloud Run Service ---

resource "google_cloud_run_service" "backend" {
  name     = "${local.name_prefix}-backend-svc"
  location = var.gcp_region

  template {
    spec {
      containers {
        image = "gcr.io/${var.gcp_project_id}/${local.name_prefix}-backend:latest"
        ports {
          container_port = 8080
        }
      }
      service_account_name = google_service_account.cloud_run_exec.email
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/maxScale"        = "10"
        "run.googleapis.com/vpc-access-connector" = google_vpc_access_connector.main.id
      }
    }
  }
}

# --- Compute Engine Bastion Host ---

resource "google_compute_instance" "bastion" {
  name         = "${local.name_prefix}-bastion"
  machine_type = "e2-micro"
  zone         = data.google_compute_zones.available.names[0]

  boot_disk {
    initialize_params {
      image = data.google_compute_image.debian.self_link
      size  = 20
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.public[0].id
    access_config {}
  }

  service_account {
    email  = google_service_account.bastion.email
    scopes = ["cloud-platform"]
  }

  tags = ["bastion"]

  labels = { component = "bastion" }
}

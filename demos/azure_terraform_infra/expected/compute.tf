resource "google_cloudfunctions2_function" "api" {
  name     = "myapp-functions"
  location = var.region

  build_config {
    runtime     = "python312"
    entry_point = "handler"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_source.name
        object = "function-source.zip"
      }
    }
  }

  service_config {
    available_memory = "256Mi"
    environment_variables = {
      FIRESTORE_PROJECT = var.project_id
      PUBSUB_TOPIC      = google_pubsub_topic.notifications.name
    }
  }
}

resource "google_container_cluster" "main" {
  name     = "myapp-gke"
  location = var.region

  initial_node_count = 3

  node_config {
    machine_type = "e2-medium"
  }

  labels = {
    environment = "production"
  }
}

resource "google_compute_instance" "worker" {
  name         = "myapp-worker"
  machine_type = "e2-small"
  zone         = "${var.region}-a"

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
    }
  }

  network_interface {
    network = "default"
  }
}

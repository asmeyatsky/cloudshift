resource "google_compute_network" "main" {
  name                    = "myapp-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "internal" {
  name          = "internal"
  network       = google_compute_network.main.id
  ip_cidr_range = "10.0.1.0/24"
  region        = var.region
}

resource "google_compute_firewall" "allow_https" {
  name    = "myapp-allow-https"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = ["443"]
  }

  source_ranges = ["0.0.0.0/0"]
}

resource "google_compute_global_address" "main" {
  name = "myapp-ip"
}

resource "google_compute_url_map" "main" {
  name = "myapp-lb"

  default_service = google_compute_backend_service.main.id
}

# --- VPC Network ---

resource "google_compute_network" "main" {
  name                    = "${local.name_prefix}-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "public" {
  count         = 2
  name          = "${local.name_prefix}-public-${count.index}"
  ip_cidr_range = cidrsubnet(var.vpc_cidr, 8, count.index)
  region        = var.gcp_region
  network       = google_compute_network.main.id
}

resource "google_compute_subnetwork" "private" {
  count         = 2
  name          = "${local.name_prefix}-private-${count.index}"
  ip_cidr_range = cidrsubnet(var.vpc_cidr, 8, count.index + 10)
  region        = var.gcp_region
  network       = google_compute_network.main.id

  private_ip_google_access = true
}

resource "google_vpc_access_connector" "main" {
  name          = "${local.name_prefix}-connector"
  region        = var.gcp_region
  network       = google_compute_network.main.name
  ip_cidr_range = "10.8.0.0/28"
}

# --- Firewall Rules ---

resource "google_compute_firewall" "allow_internal" {
  name    = "${local.name_prefix}-allow-internal"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  source_ranges = [var.vpc_cidr]
}

resource "google_compute_firewall" "allow_ssh_bastion" {
  name    = "${local.name_prefix}-allow-ssh-bastion"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = var.allowed_ssh_cidrs
  target_tags   = ["bastion"]
}

resource "google_compute_firewall" "allow_http" {
  name    = "${local.name_prefix}-allow-http"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = ["8080"]
  }

  source_ranges = [var.vpc_cidr]
  target_tags   = ["backend"]
}

# --- API Gateway ---

resource "google_api_gateway_api" "main" {
  provider = google
  api_id   = "${local.name_prefix}-api"

  labels = { component = "api" }
}

# --- Cloud CDN with Global Backend Bucket ---

resource "google_compute_backend_bucket" "cdn" {
  name        = "${local.name_prefix}-cdn-backend"
  bucket_name = google_storage_bucket.assets.name
  enable_cdn  = true

  cdn_policy {
    cache_mode        = "CACHE_ALL_STATIC"
    default_ttl       = 3600
    max_ttl           = 86400
    serve_while_stale = 86400
  }
}

resource "google_compute_url_map" "cdn" {
  name            = "${local.name_prefix}-cdn-urlmap"
  default_service = google_compute_backend_bucket.cdn.id
}

# --- Cloud DNS Zone ---

resource "google_dns_managed_zone" "main" {
  name     = "${local.name_prefix}-zone"
  dns_name = "${var.domain_name}."

  labels = { component = "dns" }
}

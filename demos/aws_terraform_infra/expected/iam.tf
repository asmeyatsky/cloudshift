# --- Cloud Function Service Account ---

resource "google_service_account" "function_exec" {
  account_id   = "${local.name_prefix}-func-sa"
  display_name = "Cloud Function Execution Service Account"
}

resource "google_project_iam_member" "function_firestore" {
  project = var.gcp_project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.function_exec.email}"
}

resource "google_project_iam_member" "function_pubsub" {
  project = var.gcp_project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.function_exec.email}"
}

resource "google_project_iam_member" "function_storage" {
  project = var.gcp_project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.function_exec.email}"
}

resource "google_project_iam_member" "function_secretmanager" {
  project = var.gcp_project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.function_exec.email}"
}

resource "google_project_iam_member" "function_logging" {
  project = var.gcp_project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.function_exec.email}"
}

# --- Cloud Run Service Account ---

resource "google_service_account" "cloud_run_exec" {
  account_id   = "${local.name_prefix}-run-sa"
  display_name = "Cloud Run Execution Service Account"
}

resource "google_project_iam_member" "cloud_run_firestore" {
  project = var.gcp_project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.cloud_run_exec.email}"
}

resource "google_project_iam_member" "cloud_run_cloudsql" {
  project = var.gcp_project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cloud_run_exec.email}"
}

resource "google_project_iam_member" "cloud_run_logging" {
  project = var.gcp_project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.cloud_run_exec.email}"
}

# --- Bastion Service Account ---

resource "google_service_account" "bastion" {
  account_id   = "${local.name_prefix}-bastion-sa"
  display_name = "Bastion Host Service Account"
}

resource "google_project_iam_member" "bastion_compute_viewer" {
  project = var.gcp_project_id
  role    = "roles/compute.viewer"
  member  = "serviceAccount:${google_service_account.bastion.email}"
}

# --- KMS Key Ring & Crypto Key ---

resource "google_kms_key_ring" "main" {
  name     = "${local.name_prefix}-keyring"
  location = var.gcp_region
}

resource "google_kms_crypto_key" "main" {
  name            = "${local.name_prefix}-key"
  key_ring        = google_kms_key_ring.main.id
  rotation_period = "7776000s" # 90 days

  lifecycle {
    prevent_destroy = true
  }

  labels = { component = "security" }
}

resource "google_kms_crypto_key_iam_member" "function_encrypt_decrypt" {
  crypto_key_id = google_kms_crypto_key.main.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = "serviceAccount:${google_service_account.function_exec.email}"
}

# --- Secret Manager ---

resource "google_secret_manager_secret" "db_password" {
  secret_id = "${local.name_prefix}-db-password"

  replication {
    auto {}
  }

  labels = { component = "security" }
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = var.db_password
}

resource "google_secret_manager_secret" "api_keys" {
  secret_id = "${local.name_prefix}-api-keys"

  replication {
    auto {}
  }

  labels = { component = "security" }
}

resource "google_secret_manager_secret_version" "api_keys" {
  secret = google_secret_manager_secret.api_keys.id
  secret_data = jsonencode({
    stripe_key   = var.stripe_api_key
    sendgrid_key = var.sendgrid_api_key
  })
}

resource "google_secret_manager_secret_iam_member" "function_db_password" {
  secret_id = google_secret_manager_secret.db_password.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.function_exec.email}"
}

resource "google_secret_manager_secret_iam_member" "function_api_keys" {
  secret_id = google_secret_manager_secret.api_keys.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.function_exec.email}"
}

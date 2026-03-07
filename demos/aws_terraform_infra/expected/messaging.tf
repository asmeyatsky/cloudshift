# --- Pub/Sub Processing Topic & Subscription ---

resource "google_pubsub_topic" "processing" {
  name = "${local.name_prefix}-processing"

  message_storage_policy {
    allowed_persistence_regions = [var.gcp_region]
  }

  labels = { component = "messaging" }
}

resource "google_pubsub_subscription" "processing" {
  name  = "${local.name_prefix}-processing-sub"
  topic = google_pubsub_topic.processing.id

  ack_deadline_seconds       = 120
  message_retention_duration = "345600s"

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.processing_dlq.id
    max_delivery_attempts = 3
  }

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  labels = { component = "messaging" }
}

resource "google_pubsub_topic" "processing_dlq" {
  name = "${local.name_prefix}-processing-dlq"

  message_retention_duration = "1209600s"

  labels = { component = "messaging" }
}

resource "google_pubsub_subscription" "processing_dlq" {
  name  = "${local.name_prefix}-processing-dlq-sub"
  topic = google_pubsub_topic.processing_dlq.id

  labels = { component = "messaging" }
}

# --- Pub/Sub Notifications Topic ---

resource "google_pubsub_topic" "notifications" {
  name       = "${local.name_prefix}-notifications"
  kms_key_name = google_kms_crypto_key.main.id

  labels = { component = "messaging" }
}

resource "google_pubsub_subscription" "notifications_push" {
  name  = "${local.name_prefix}-notifications-push"
  topic = google_pubsub_topic.notifications.id

  push_config {
    push_endpoint = var.notification_push_endpoint
  }
}

# --- Cloud Scheduler (EventBridge equivalent) ---

resource "google_cloud_scheduler_job" "daily_cleanup" {
  name        = "${local.name_prefix}-daily-cleanup"
  description = "Triggers daily data cleanup Cloud Function"
  schedule    = "0 2 * * *"
  time_zone   = "UTC"
  region      = var.gcp_region

  http_target {
    http_method = "POST"
    uri         = google_cloudfunctions2_function.stream_processor.url

    oidc_token {
      service_account_email = google_service_account.function_exec.email
    }
  }
}

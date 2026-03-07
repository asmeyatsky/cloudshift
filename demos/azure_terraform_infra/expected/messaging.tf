resource "google_pubsub_topic" "orders" {
  name = "orders"

  labels = {
    environment = "production"
  }
}

resource "google_pubsub_subscription" "orders_sub" {
  name  = "orders-sub"
  topic = google_pubsub_topic.orders.name

  ack_deadline_seconds = 60
  message_retention_duration = "1209600s"

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.orders_dlq.id
    max_delivery_attempts = 5
  }
}

resource "google_pubsub_topic" "notifications" {
  name = "notifications"
}

resource "google_pubsub_subscription" "email" {
  name  = "email-sub"
  topic = google_pubsub_topic.notifications.name

  ack_deadline_seconds = 20
}

resource "google_pubsub_topic" "app_events" {
  name = "app-events"
}

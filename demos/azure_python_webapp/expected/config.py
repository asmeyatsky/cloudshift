"""GCP-specific configuration for the web application."""

import os


# Google Cloud Storage
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "app-uploads")

# Google Cloud Firestore
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "my-gcp-project")
FIRESTORE_COLLECTION = os.environ.get("FIRESTORE_COLLECTION", "items")

# Google Cloud Pub/Sub
PUBSUB_QUEUE_TOPIC = os.environ.get("PUBSUB_QUEUE_TOPIC", "tasks")
PUBSUB_QUEUE_SUBSCRIPTION = os.environ.get("PUBSUB_QUEUE_SUBSCRIPTION", "tasks-sub")
PUBSUB_NOTIFICATION_TOPIC = os.environ.get("PUBSUB_NOTIFICATION_TOPIC", "notifications")

# Google Cloud Secret Manager
GCP_SECRET_PROJECT = os.environ.get("GCP_SECRET_PROJECT", "my-gcp-project")

# GCP Service Account
GOOGLE_APPLICATION_CREDENTIALS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
GCP_SERVICE_ACCOUNT_EMAIL = os.environ.get("GCP_SERVICE_ACCOUNT_EMAIL", "")

# Application settings
APP_PORT = int(os.environ.get("APP_PORT", "8080"))
APP_DEBUG = os.environ.get("APP_DEBUG", "false").lower() == "true"

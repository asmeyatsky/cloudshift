"""GCP-specific configuration for the microservice."""

import os

# GCP Project and Region
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "my-gcp-project")
GCP_REGION = os.environ.get("GCP_REGION", "us-central1")

# Cloud Storage Configuration
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "myapp-data-bucket")
GCS_UPLOAD_PREFIX = "uploads/"
GCS_SIGNED_URL_EXPIRY = 3600  # seconds

# Firestore Configuration
FIRESTORE_COLLECTION = os.environ.get("FIRESTORE_COLLECTION", "myapp-items")

# Pub/Sub Configuration
PUBSUB_TOPIC = os.environ.get("PUBSUB_TOPIC", "myapp-tasks")
PUBSUB_SUBSCRIPTION = os.environ.get("PUBSUB_SUBSCRIPTION", "myapp-tasks-sub")
PUBSUB_NOTIFICATION_TOPIC = os.environ.get(
    "PUBSUB_NOTIFICATION_TOPIC", "myapp-notifications"
)
PUBSUB_DLQ_SUBSCRIPTION = os.environ.get(
    "PUBSUB_DLQ_SUBSCRIPTION", "myapp-tasks-dlq-sub"
)

# Secret Manager
SECRET_NAME = os.environ.get("SECRET_NAME", "myapp-api-keys")

# Service Account for impersonation
IMPERSONATE_SERVICE_ACCOUNT = os.environ.get(
    "IMPERSONATE_SERVICE_ACCOUNT",
    f"myapp-cross-account@{GCP_PROJECT_ID}.iam.gserviceaccount.com",
)

# Cloud Logging
LOG_NAME = f"myapp-{os.environ.get('ENV', 'dev')}"

# Cloud Monitoring namespace
MONITORING_NAMESPACE = "custom.googleapis.com/myapp"

# Runtime Config / parameter prefix
PARAMETER_PREFIX = f"myapp-{os.environ.get('ENV', 'dev')}"

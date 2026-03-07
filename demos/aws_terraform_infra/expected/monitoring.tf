# --- Cloud Logging Log Sinks ---

resource "google_logging_project_sink" "function_api" {
  name        = "${local.name_prefix}-func-api-logs"
  destination = "logging.googleapis.com/projects/${var.gcp_project_id}/locations/${var.gcp_region}/buckets/${local.name_prefix}-logs"

  filter = "resource.type=\"cloud_function\" AND resource.labels.function_name=\"${google_cloudfunctions2_function.api_handler.name}\""
}

resource "google_logging_project_sink" "function_processor" {
  name        = "${local.name_prefix}-func-processor-logs"
  destination = "logging.googleapis.com/projects/${var.gcp_project_id}/locations/${var.gcp_region}/buckets/${local.name_prefix}-logs"

  filter = "resource.type=\"cloud_function\" AND resource.labels.function_name=\"${google_cloudfunctions2_function.stream_processor.name}\""
}

resource "google_logging_project_sink" "cloud_run_backend" {
  name        = "${local.name_prefix}-run-backend-logs"
  destination = "logging.googleapis.com/projects/${var.gcp_project_id}/locations/${var.gcp_region}/buckets/${local.name_prefix}-logs"

  filter = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${google_cloud_run_service.backend.name}\""
}

# --- Monitoring Alert Policies ---

resource "google_monitoring_alert_policy" "function_errors" {
  display_name = "${local.name_prefix}-function-errors"
  combiner     = "OR"

  conditions {
    display_name = "Cloud Function error rate"

    condition_threshold {
      filter          = "resource.type=\"cloud_function\" AND metric.type=\"cloudfunctions.googleapis.com/function/execution_count\" AND metric.labels.status!=\"ok\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 5

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.name]
}

resource "google_monitoring_alert_policy" "cloudsql_cpu" {
  display_name = "${local.name_prefix}-cloudsql-cpu"
  combiner     = "OR"

  conditions {
    display_name = "Cloud SQL CPU utilization high"

    condition_threshold {
      filter          = "resource.type=\"cloudsql_database\" AND metric.type=\"cloudsql.googleapis.com/database/cpu/utilization\""
      duration        = "900s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.8

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.name]
}

resource "google_monitoring_notification_channel" "email" {
  display_name = "${local.name_prefix}-email-alerts"
  type         = "email"

  labels = {
    email_address = var.alert_email
  }
}

# --- Monitoring Dashboard ---

resource "google_monitoring_dashboard" "main" {
  dashboard_json = jsonencode({
    displayName = "${local.name_prefix}-overview"
    gridLayout = {
      widgets = [
        {
          title = "Cloud Function Invocations"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type=\"cloud_function\" AND metric.type=\"cloudfunctions.googleapis.com/function/execution_count\""
                }
              }
            }]
          }
        }
      ]
    }
  })
}

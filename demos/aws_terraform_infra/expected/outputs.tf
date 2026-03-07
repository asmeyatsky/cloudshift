output "vpc_id" {
  description = "VPC Network ID"
  value       = google_compute_network.main.id
}

output "api_gateway_url" {
  description = "API Gateway URL"
  value       = google_api_gateway_api.main.managed_service
}

output "cdn_url" {
  description = "CDN URL map self link"
  value       = google_compute_url_map.cdn.self_link
}

output "function_api_name" {
  description = "API handler Cloud Function name"
  value       = google_cloudfunctions2_function.api_handler.name
}

output "firestore_database_name" {
  description = "Firestore database name"
  value       = google_firestore_database.main.name
}

output "cloudsql_connection" {
  description = "Cloud SQL instance connection name"
  value       = google_sql_database_instance.postgres.connection_name
}

output "redis_host" {
  description = "Memorystore Redis host"
  value       = google_redis_instance.main.host
}

output "pubsub_processing_topic" {
  description = "Pub/Sub processing topic name"
  value       = google_pubsub_topic.processing.name
}

output "pubsub_notifications_topic" {
  description = "Pub/Sub notifications topic ID"
  value       = google_pubsub_topic.notifications.id
}

output "data_bucket_name" {
  description = "Data storage bucket name"
  value       = google_storage_bucket.data.name
}

output "cloud_run_url" {
  description = "Cloud Run service URL"
  value       = google_cloud_run_service.backend.status[0].url
}

output "dns_zone_name" {
  description = "Cloud DNS managed zone name"
  value       = google_dns_managed_zone.main.name
}

output "kms_key_id" {
  description = "KMS crypto key ID"
  value       = google_kms_crypto_key.main.id
}

output "bastion_ip" {
  description = "Bastion host external IP"
  value       = google_compute_instance.bastion.network_interface[0].access_config[0].nat_ip
}

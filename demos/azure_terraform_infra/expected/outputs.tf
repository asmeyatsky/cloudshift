output "storage_bucket_name" {
  value = google_storage_bucket.main.name
}

output "firestore_database" {
  value = google_firestore_database.main.name
}

output "gke_cluster_name" {
  value = google_container_cluster.main.name
}

output "cloud_function_url" {
  value = google_cloudfunctions2_function.api.url
}

output "pubsub_topic" {
  value = google_pubsub_topic.orders.name
}

output "cloud_sql_connection" {
  value = google_sql_database_instance.main.connection_name
}

output "secret_manager_id" {
  value = google_secret_manager_secret.main.id
}

output "load_balancer_ip" {
  value = google_compute_global_address.main.address
}

output "cloud_run_url" {
  description = "Public URL of the deployed portal."
  value       = google_cloud_run_v2_service.app.uri
}

output "instance_connection_name" {
  description = "Cloud SQL instance connection name (PROJECT:REGION:INSTANCE) — used by the Cloud SQL Auth Proxy for local/manual admin access."
  value       = google_sql_database_instance.northstar.connection_name
}

output "artifact_registry_repo" {
  description = "Where to push the app image — deploy/setup_gcp.sh does this for you."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.app.repository_id}"
}

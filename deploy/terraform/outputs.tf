output "cloud_run_url" {
  description = "Public URL of the deployed portal + AI copilot."
  value       = google_cloud_run_v2_service.app.uri
}

output "artifact_registry_repo" {
  description = "Where to push the app image — deploy/setup_gcp.sh does this for you."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.app.repository_id}"
}

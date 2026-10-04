# ------------------------------------------
# ARTIFACT REGISTRY — this deployment's own Docker repo, separate from
# Legacy-System's "northstar-legacy" repo, so the two Terraform states
# never share ownership of the same resource. deploy/setup_gcp.sh builds
# and pushes into this before Cloud Run can reference a real image.
# ------------------------------------------
resource "google_artifact_registry_repository" "app" {
  project       = var.project_id
  location      = var.region
  repository_id = "northstar-legacy-with-ai"
  format        = "DOCKER"

  depends_on = [google_project_service.required]
}

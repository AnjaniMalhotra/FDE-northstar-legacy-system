# ------------------------------------------
# ARTIFACT REGISTRY — one Docker repo for the app image. deploy/setup_gcp.sh
# builds and pushes into this before Cloud Run can reference a real image.
# ------------------------------------------
resource "google_artifact_registry_repository" "app" {
  project       = var.project_id
  location      = var.region
  repository_id = "northstar-legacy"
  format        = "DOCKER"

  depends_on = [google_project_service.required]
}

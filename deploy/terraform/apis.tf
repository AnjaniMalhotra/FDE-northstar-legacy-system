# ------------------------------------------
# APIS — enabled idempotently; a no-op if already on (as they already are,
# from Northstar-Legacy-System's own deployment into this same project).
# Listed explicitly so a fresh GCP project works too. disable_on_destroy
# stays false so tearing down this deployment never disables an API
# Northstar-Legacy-System's own deployment still depends on.
# ------------------------------------------
locals {
  required_apis = [
    "sqladmin.googleapis.com",
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudbuild.googleapis.com",
    "iam.googleapis.com",
  ]
}

resource "google_project_service" "required" {
  for_each = toset(local.required_apis)

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

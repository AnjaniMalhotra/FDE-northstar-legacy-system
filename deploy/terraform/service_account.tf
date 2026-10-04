# ------------------------------------------
# CLOUD RUN SERVICE ACCOUNT — a dedicated identity for the running app,
# not the Compute Engine default service account. Only granted exactly
# what it needs: connect to this one Cloud SQL instance, read these three
# secrets. Same "no shared/broad login" discipline the Postgres roles in
# backend/scripts/northstar_web_security.sql already follow.
# ------------------------------------------
resource "google_service_account" "app" {
  project      = var.project_id
  account_id   = "northstar-legacy-app"
  display_name = "Northstar Legacy System — Cloud Run app"
}

resource "google_project_iam_member" "cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.app.email}"
}

resource "google_secret_manager_secret_iam_member" "secret_accessor" {
  for_each  = google_secret_manager_secret.password
  project   = var.project_id
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.app.email}"
}

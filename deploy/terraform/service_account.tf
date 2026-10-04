# ------------------------------------------
# CLOUD RUN SERVICE ACCOUNT — a dedicated identity for this app, separate
# from Northstar-Legacy-System's own (northstar-legacy-app). Granted
# exactly what it needs: connect to the shared Cloud SQL instance, read
# its own 6 new secrets, and read the 2 portal-role secrets it shares with
# Legacy-System (same database, same app/admin roles) — never write
# access to anything Legacy-System's own service account owns.
# ------------------------------------------
resource "google_service_account" "app" {
  project      = var.project_id
  account_id   = "northstar-legacy-with-ai"
  display_name = "Northstar Legacy With AI — Cloud Run app"
}

resource "google_project_iam_member" "cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.app.email}"
}

# Its own 6 new secrets (the 4 AI-role passwords + 2 API keys)
resource "google_secret_manager_secret_iam_member" "own_secret_accessor" {
  for_each  = google_secret_manager_secret.ai
  project   = var.project_id
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.app.email}"
}

# The 3 portal-role secrets, owned by Legacy-System's own Terraform state —
# this only grants read access on them, never recreates or redefines them.
resource "google_secret_manager_secret_iam_member" "shared_secret_accessor" {
  for_each = {
    db-admin = data.google_secret_manager_secret.db_admin_password.secret_id
    app-role = data.google_secret_manager_secret.app_role_password.secret_id
    fde-role = data.google_secret_manager_secret.fde_role_password.secret_id
  }
  project   = var.project_id
  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.app.email}"
}

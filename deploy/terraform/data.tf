# ------------------------------------------
# EXISTING RESOURCES — read-only references into what Northstar-Legacy-
# System's own Terraform state already created and owns. Data sources, not
# resources: this state never manages (and so can never accidentally
# delete) the Cloud SQL instance or the two portal-role secrets — it only
# looks them up live from GCP by name. The two deployments stay on
# completely independent Terraform states that can never conflict.
# ------------------------------------------
data "google_sql_database_instance" "northstar" {
  project = var.project_id
  name    = "northstar-web-db"
}

data "google_secret_manager_secret" "db_admin_password" {
  project   = var.project_id
  secret_id = "db-admin-password"
}

data "google_secret_manager_secret" "app_role_password" {
  project   = var.project_id
  secret_id = "app-role-password"
}

data "google_secret_manager_secret" "fde_role_password" {
  project   = var.project_id
  secret_id = "fde-role-password"
}

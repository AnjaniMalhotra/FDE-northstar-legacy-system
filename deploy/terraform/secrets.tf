# ------------------------------------------
# SECRET MANAGER — the three passwords above, stored once here. Cloud Run
# (run.tf) reads them at container start as env vars; nothing ever writes
# a real password into a Terraform state diff a human reads casually, or
# into a checked-in file.
# ------------------------------------------
locals {
  secret_values = {
    db-admin-password = random_password.db_admin.result
    app-role-password = random_password.app_role.result
    fde-role-password = random_password.fde_role.result
  }
}

resource "google_secret_manager_secret" "password" {
  for_each  = local.secret_values
  project   = var.project_id
  secret_id = each.key

  replication {
    auto {}
  }

  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret_version" "password" {
  for_each    = local.secret_values
  secret      = google_secret_manager_secret.password[each.key].id
  secret_data = each.value
}

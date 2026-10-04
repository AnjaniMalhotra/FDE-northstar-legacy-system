# ------------------------------------------
# NEW SECRETS — the 4 AI-role database passwords (generated here, same as
# Northstar-Legacy-System generates its own 3), plus the 2 real API keys
# this deployment needs that Legacy-System's never did. The portal's own
# db-admin-password/app-role-password/fde-role-password secrets are NOT
# recreated here — data.tf reads those that already exist.
# ------------------------------------------
resource "random_password" "db_agent" {
  length  = 24
  special = false
}

resource "random_password" "db_analyst" {
  length  = 24
  special = false
}

resource "random_password" "db_manager" {
  length  = 24
  special = false
}

resource "random_password" "db_human_admin" {
  length  = 24
  special = false
}

locals {
  generated_secret_values = {
    db-agent-password       = random_password.db_agent.result
    db-analyst-password     = random_password.db_analyst.result
    db-manager-password     = random_password.db_manager.result
    db-human-admin-password = random_password.db_human_admin.result
  }
  provided_secret_values = {
    pinecone-api-key = var.pinecone_api_key
    openai-api-key   = var.openai_api_key
  }
  secret_values = merge(local.generated_secret_values, local.provided_secret_values)
}

resource "google_secret_manager_secret" "ai" {
  for_each  = local.secret_values
  project   = var.project_id
  secret_id = each.key

  replication {
    auto {}
  }

  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret_version" "ai" {
  for_each    = local.secret_values
  secret      = google_secret_manager_secret.ai[each.key].id
  secret_data = each.value
}

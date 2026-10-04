# ------------------------------------------
# GENERATED PASSWORDS — created once by Terraform, then stored in Secret
# Manager (secrets.tf) rather than ever appearing in a .tfvars file or a
# CREATE ROLE literal (see backend/scripts/northstar_web_security.sql,
# which takes these as psql variables instead).
# ------------------------------------------
resource "random_password" "db_admin" {
  length  = 24
  special = false
}

resource "random_password" "app_role" {
  length  = 24
  special = false
}

resource "random_password" "fde_role" {
  length  = 24
  special = false
}

# ------------------------------------------
# CLOUD SQL INSTANCE — Postgres, same engine this project has always used
# locally, so backend/scripts/*.sql needs zero changes to run against it.
# ------------------------------------------
resource "google_sql_database_instance" "northstar" {
  name             = "northstar-web-db"
  project          = var.project_id
  region           = var.region
  database_version = "POSTGRES_16"

  settings {
    tier    = var.sql_tier
    # Explicit, not the project default — this project's default Cloud SQL
    # edition is ENTERPRISE_PLUS, which rejects classic shared-core tiers
    # like db-f1-micro (discovered via a real failed apply, not foreseeable
    # from `terraform plan` alone — tier/edition compatibility is only
    # validated server-side). ENTERPRISE is the edition db-f1-micro is
    # actually valid under.
    edition = "ENTERPRISE"
    ip_configuration {
      ipv4_enabled = true
    }
    backup_configuration {
      enabled = true
    }
  }

  deletion_protection = false

  depends_on = [google_project_service.required]
}

resource "google_sql_user" "admin" {
  project  = var.project_id
  instance = google_sql_database_instance.northstar.name
  name     = "postgres"
  password = random_password.db_admin.result
}

resource "google_sql_database" "northstar_web" {
  project  = var.project_id
  instance = google_sql_database_instance.northstar.name
  name     = "northstar_web"
}

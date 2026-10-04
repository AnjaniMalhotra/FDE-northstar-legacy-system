# ------------------------------------------
# CLOUD RUN SERVICE — one container, serving both the API and the static
# site (see backend/northstar_web_api/main.py). Connects to Cloud SQL over
# the Unix socket this resource's cloud_sql_instance volume mounts at
# /cloudsql/<connection_name> — backend/northstar_web_api/db.py picks that
# path up automatically whenever INSTANCE_CONNECTION_NAME is set.
# ------------------------------------------
resource "google_cloud_run_v2_service" "app" {
  name     = "northstar-legacy-system"
  project  = var.project_id
  location = var.region

  template {
    service_account = google_service_account.app.email

    containers {
      image = var.image

      env {
        name  = "DB_ADMIN_USER"
        value = "postgres"
      }
      env {
        name  = "NORTHSTAR_WEB_DB_NAME"
        value = "northstar_web"
      }
      env {
        name  = "NORTHSTAR_WEB_FDE_USER"
        value = "northstar_web_fde_ro"
      }
      env {
        name  = "INSTANCE_CONNECTION_NAME"
        value = google_sql_database_instance.northstar.connection_name
      }

      env {
        name = "DB_ADMIN_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.password["db-admin-password"].secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "NORTHSTAR_WEB_APP_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.password["app-role-password"].secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "NORTHSTAR_WEB_FDE_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.password["fde-role-password"].secret_id
            version = "latest"
          }
        }
      }

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }
    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [google_sql_database_instance.northstar.connection_name]
      }
    }
  }

  depends_on = [
    google_project_iam_member.cloudsql_client,
    google_secret_manager_secret_iam_member.secret_accessor,
  ]
}

# ------------------------------------------
# PUBLIC ACCESS — this is a teaching demo, meant to be opened by anyone
# with the URL, the same as running it locally. Tighten this (remove
# allUsers, front it with IAP) before using this pattern for anything real.
# ------------------------------------------
resource "google_cloud_run_v2_service_iam_member" "public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.app.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ------------------------------------------
# CLOUD RUN SERVICE — one container serving the portal AND the AI copilot
# (see backend/northstar_web_api/main.py). Connects to the SAME Cloud SQL
# instance Northstar-Legacy-System uses — data.google_sql_database_instance
# above, not a resource this state owns — over the Unix socket this
# resource's cloud_sql_instance volume mounts at /cloudsql/<connection_name>.
# LLM_PROVIDER is OPENAI here, not the local-dev OLLAMA default: there's no
# Ollama runtime in this container for it to reach, and OpenAI is already
# the tested, reliable path (see the TDD, §2.3).
# ------------------------------------------
resource "google_cloud_run_v2_service" "app" {
  name                = "northstar-legacy-with-ai"
  project             = var.project_id
  location            = var.region
  deletion_protection = false

  template {
    service_account = google_service_account.app.email

    containers {
      image = var.image

      # Cloud Run's default (512Mi) isn't enough here — confirmed by a real
      # failed deploy ("container ran out of memory"), not a guess. PyTorch
      # plus the loaded embedding model plus a 5,000-row batched data
      # generation pass all resident at once needs real headroom; Legacy-
      # System's own container never needed this block at all, since it
      # carries none of that.
      resources {
        limits = {
          memory = "2Gi"
          cpu    = "2"
        }
      }

      # --- static config, no secret involved ---
      env {
        name  = "DB_ADMIN_USER"
        value = "postgres"
      }
      env {
        name  = "NORTHSTAR_WEB_DB_NAME"
        value = "northstar_web"
      }
      env {
        name  = "DB_NAME"
        value = "northstar_web"
      }
      env {
        name  = "NORTHSTAR_WEB_FDE_USER"
        value = "northstar_web_fde_ro"
      }
      env {
        name  = "DB_AGENT_USER"
        value = "northstar_web_agent"
      }
      env {
        name  = "AUTH_MODE"
        value = "LOCAL_DEV"
      }
      env {
        name  = "POC_DEMO_STAGE"
        value = "PART_2"
      }
      env {
        name  = "LLM_PROVIDER"
        value = "OPENAI"
      }
      env {
        name  = "OPENAI_MODEL"
        value = "gpt-4o-mini"
      }
      env {
        name  = "INSTANCE_CONNECTION_NAME"
        value = data.google_sql_database_instance.northstar.connection_name
      }

      # --- shared portal-role secrets (owned by Legacy-System's state) ---
      env {
        name = "DB_ADMIN_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = data.google_secret_manager_secret.db_admin_password.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "NORTHSTAR_WEB_APP_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = data.google_secret_manager_secret.app_role_password.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "NORTHSTAR_WEB_FDE_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = data.google_secret_manager_secret.fde_role_password.secret_id
            version = "latest"
          }
        }
      }

      # --- this deployment's own secrets ---
      env {
        name = "DB_AGENT_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.ai["db-agent-password"].secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "DB_ANALYST_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.ai["db-analyst-password"].secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "DB_MANAGER_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.ai["db-manager-password"].secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "DB_HUMAN_ADMIN_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.ai["db-human-admin-password"].secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "PINECONE_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.ai["pinecone-api-key"].secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "OPENAI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.ai["openai-api-key"].secret_id
            version = "latest"
          }
        }
      }

      # A generous first-boot allowance: the container runs the full
      # bootstrap (schema, security, data scale-up, RAG ingestion into
      # Pinecone) before uvicorn ever starts listening, which the default
      # startup probe window isn't long enough for — confirmed by a real
      # failed deploy, not a guess. Only matters for the first cold start;
      # bootstrap.sh is idempotent and fast on every one after.
      startup_probe {
        tcp_socket {
          port = 8080
        }
        initial_delay_seconds = 0
        timeout_seconds       = 30
        period_seconds        = 30
        failure_threshold     = 20
      }

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }
    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [data.google_sql_database_instance.northstar.connection_name]
      }
    }
  }

  depends_on = [
    google_project_iam_member.cloudsql_client,
    google_secret_manager_secret_iam_member.own_secret_accessor,
    google_secret_manager_secret_iam_member.shared_secret_accessor,
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

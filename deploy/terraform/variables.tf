# ------------------------------------------
# VARIABLES — everything a first-time user needs to set is here, with a
# sensible default. See deploy/terraform.tfvars.example.
# ------------------------------------------
variable "project_id" {
  description = "GCP project ID to deploy into."
  type        = string
}

variable "region" {
  description = "GCP region for Cloud SQL, Cloud Run, and Artifact Registry."
  type        = string
  default     = "us-central1"
}

variable "sql_tier" {
  description = "Cloud SQL machine tier — db-f1-micro is the cheapest that still runs Postgres reliably."
  type        = string
  default     = "db-f1-micro"
}

variable "image" {
  description = <<-EOT
    Full Artifact Registry image reference for the app container
    (e.g. us-central1-docker.pkg.dev/PROJECT/northstar-legacy/app:latest).
    Left as a public placeholder on first apply, before any image has been
    pushed — see deploy/setup_gcp.sh, which applies twice: once to create
    the Artifact Registry repo, then again with the real image after
    building and pushing it.
  EOT
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

# ------------------------------------------
# VARIABLES — everything a first-time user needs to set is here, with a
# sensible default. See deploy/terraform.tfvars.example. No sql_tier here —
# this project connects to Northstar-Legacy-System's own Cloud SQL instance
# (data.tf) rather than creating a second one for the same database.
# ------------------------------------------
variable "project_id" {
  description = "GCP project ID to deploy into — must already have Northstar-Legacy-System's Cloud SQL instance (northstar-web-db) deployed."
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run and Artifact Registry. Must match the region northstar-web-db was created in."
  type        = string
  default     = "us-central1"
}

variable "image" {
  description = <<-EOT
    Full Artifact Registry image reference for the app container
    (e.g. us-central1-docker.pkg.dev/PROJECT/northstar-legacy-with-ai/app:latest).
    Left as a public placeholder on first apply, before any image has been
    pushed — see deploy/setup_gcp.sh, which applies twice: once to create
    the Artifact Registry repo, then again with the real image after
    building and pushing it.
  EOT
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "pinecone_api_key" {
  description = "Pinecone API key for the RAG policy index — never committed; passed via TF_VAR_pinecone_api_key at apply time."
  type        = string
  sensitive   = true
}

variable "openai_api_key" {
  description = "OpenAI API key — the agent's reasoning model in this deployment (LLM_PROVIDER=OPENAI; no Ollama runtime in the container). Never committed."
  type        = string
  sensitive   = true
}

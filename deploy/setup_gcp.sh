#!/usr/bin/env bash
# First-time GCP deployment, from your own account: creates this
# deployment's own secrets, Artifact Registry repo, service account, and
# Cloud Run service via Terraform — reusing Northstar-Legacy-System's
# already-deployed Cloud SQL instance rather than creating a second one
# (see deploy/terraform/data.tf) — then builds and pushes the app image
# and points Cloud Run at it. The database itself is bootstrapped
# automatically the first time the container starts (see
# docker-entrypoint.sh) — no separate seeding step here.
#
# Requires: Northstar-Legacy-System already deployed into this same
# project (bash ../Northstar-Legacy-System/deploy/setup_gcp.sh first),
# gcloud (already logged in), terraform, docker, and a .env in this
# project's root with real PINECONE_API_KEY/OPENAI_API_KEY values — never
# written into any tracked file, only read here and passed to Terraform
# as TF_VAR_ environment variables.
#
# Run from the project root: bash deploy/setup_gcp.sh
set -euo pipefail

cd "$(dirname "$0")/.."   # project root

PROJECT_ID="${1:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-us-central1}"

if [ -z "$PROJECT_ID" ]; then
    echo "Usage: bash deploy/setup_gcp.sh <PROJECT_ID>   (or set it with 'gcloud config set project ...')"
    exit 1
fi

if [ ! -f .env ]; then
    echo "[setup] ERROR: .env not found. Copy .env.example to .env and fill in a real"
    echo "[setup] PINECONE_API_KEY and OPENAI_API_KEY first — both are required here."
    exit 1
fi
set -a && source .env && set +a
if [ -z "${PINECONE_API_KEY:-}" ] || [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "[setup] ERROR: PINECONE_API_KEY and OPENAI_API_KEY must both be set in .env."
    exit 1
fi
export TF_VAR_pinecone_api_key="$PINECONE_API_KEY"
export TF_VAR_openai_api_key="$OPENAI_API_KEY"

echo "[setup] Project: $PROJECT_ID   Region: $REGION"

# ------------------------------------------
# STEP 1 — Terraform creates the new secrets, Artifact Registry repo, and
# service account, reading Legacy-System's existing Cloud SQL instance and
# portal-role secrets rather than recreating them. Cloud Run is created
# too, pointed at a public placeholder image for now — updated to the
# real one in step 3.
# ------------------------------------------
echo "[setup] Terraform: creating infrastructure..."
terraform -chdir=deploy/terraform init
terraform -chdir=deploy/terraform apply \
    -var="project_id=$PROJECT_ID" -var="region=$REGION" -auto-approve

# ------------------------------------------
# STEP 2 — Build and push the app image via Cloud Build (no local Docker
# needed for this step; Cloud Build runs it in GCP). Tagged with a
# timestamp, not :latest — Terraform only redeploys Cloud Run when the
# image string it manages actually changes, so a fixed tag would silently
# leave a stale revision running on every re-run of this script. Expect
# this to take noticeably longer than Legacy-System's own image — this
# one bundles the AI stack (PyTorch for local embeddings, LangGraph, etc).
# ------------------------------------------
REPO=$(terraform -chdir=deploy/terraform output -raw artifact_registry_repo)
IMAGE="$REPO/app:$(date +%Y%m%d%H%M%S)"

echo "[setup] Building and pushing $IMAGE (this one's bigger than Legacy-System's — may take a few minutes)..."
gcloud builds submit --project "$PROJECT_ID" --tag "$IMAGE" .

# ------------------------------------------
# STEP 3 — Terraform again, now pointing Cloud Run at the real image.
# ------------------------------------------
echo "[setup] Terraform: pointing Cloud Run at the real image..."
terraform -chdir=deploy/terraform apply \
    -var="project_id=$PROJECT_ID" -var="region=$REGION" -var="image=$IMAGE" -auto-approve

URL=$(terraform -chdir=deploy/terraform output -raw cloud_run_url)
echo "[setup] Done. First load will take a little longer — the database is bootstrapping itself."
echo "[setup] Portal + AI copilot: $URL"

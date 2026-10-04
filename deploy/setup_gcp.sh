#!/usr/bin/env bash
# First-time GCP deployment, from your own account: creates the Cloud SQL
# instance, Secret Manager secrets, Artifact Registry repo, and the Cloud
# Run service via Terraform, then builds and pushes the app image and
# points Cloud Run at it. The database itself is bootstrapped automatically
# the first time the container starts (see docker-entrypoint.sh) — no
# separate seeding step here.
#
# Requires: gcloud (already logged in — `gcloud auth login`), terraform,
# docker. Run from the project root: bash deploy/setup_gcp.sh
set -euo pipefail

cd "$(dirname "$0")/.."   # project root

PROJECT_ID="${1:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-us-central1}"

if [ -z "$PROJECT_ID" ]; then
    echo "Usage: bash deploy/setup_gcp.sh <PROJECT_ID>   (or set it with 'gcloud config set project ...')"
    exit 1
fi

echo "[setup] Project: $PROJECT_ID   Region: $REGION"

# ------------------------------------------
# STEP 1 — Terraform creates Cloud SQL, secrets, the Artifact Registry
# repo, and the service account. Cloud Run is created too, pointed at a
# public placeholder image for now — updated to the real one in step 3.
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
# leave a stale revision running on every re-run of this script.
# ------------------------------------------
REPO=$(terraform -chdir=deploy/terraform output -raw artifact_registry_repo)
IMAGE="$REPO/app:$(date +%Y%m%d%H%M%S)"

echo "[setup] Building and pushing $IMAGE..."
gcloud builds submit --project "$PROJECT_ID" --tag "$IMAGE" .

# ------------------------------------------
# STEP 3 — Terraform again, now pointing Cloud Run at the real image.
# ------------------------------------------
echo "[setup] Terraform: pointing Cloud Run at the real image..."
terraform -chdir=deploy/terraform apply \
    -var="project_id=$PROJECT_ID" -var="region=$REGION" -var="image=$IMAGE" -auto-approve

URL=$(terraform -chdir=deploy/terraform output -raw cloud_run_url)
echo "[setup] Done. First load will take a little longer — the database is bootstrapping itself."
echo "[setup] Portal: $URL"

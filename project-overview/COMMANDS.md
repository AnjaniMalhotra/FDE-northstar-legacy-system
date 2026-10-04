# Commands — GCP Deployment

Real, tested commands for deploying `Northstar-Legacy-System` and `Northstar-Legacy-With-AI` to
GCP, and for tearing them back down. Every command below was actually run once, against a real
GCP project, while writing this file — not transcribed from the Terraform source and assumed to
work.

**Order matters.** `Northstar-Legacy-With-AI` reads `Northstar-Legacy-System`'s Cloud SQL instance
and three of its Secret Manager secrets as Terraform *data sources* — it never creates its own copy
of either. Deploy Legacy-System first, always.

---

## 0. Prerequisites

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

Also required: `terraform` (>= 1.5), `docker`, and a real `.env` in each project's root (copy from
that project's own `.env.example`) — `Northstar-Legacy-With-AI`'s deploy script specifically
refuses to run without a real `PINECONE_API_KEY` and `OPENAI_API_KEY` already in its `.env`.

---

## 1. Deploy Northstar-Legacy-System

```bash
cd "Northstar-Legacy-System"
bash deploy/setup_gcp.sh YOUR_PROJECT_ID
```

This one script does all three steps (Terraform creates Cloud SQL/secrets/Artifact Registry/Cloud
Run with a placeholder image → Cloud Build builds and pushes the real image → Terraform points
Cloud Run at it). First boot bootstraps the database itself (schema, security roles, starter seed,
then scales up to **25 carriers / 100 shippers / 5,000 invoices** — see `generate_more_data.py`).

```bash
# Verify
URL=$(terraform -chdir=deploy/terraform output -raw cloud_run_url)
curl -s -o /dev/null -w "%{http_code}\n" "$URL/"
curl -s -X POST "$URL/api/auth/login" -H "Content-Type: application/json" \
  -d '{"portal":"employee","email":"admin@northstarfreight.com","password":"demo123"}'
```

---

## 2. Deploy Northstar-Legacy-With-AI

```bash
cd "../Northstar-Legacy-With-AI"
bash deploy/setup_gcp.sh YOUR_PROJECT_ID
```

Same three-step pattern, but this image is bigger (bundles PyTorch + the local embeddings model
for RAG) — expect the Cloud Build step to take noticeably longer than Legacy-System's.

```bash
# Verify
URL=$(terraform -chdir=deploy/terraform output -raw cloud_run_url)
curl -s -o /dev/null -w "%{http_code}\n" "$URL/"
TOKEN=/tmp/cookies.txt
curl -s -c "$TOKEN" -X POST "$URL/api/auth/login" -H "Content-Type: application/json" \
  -d '{"portal":"employee","email":"admin@northstarfreight.com","password":"demo123"}'
curl -s -b "$TOKEN" "$URL/api/ai/me"          # confirms the single-login AI identity derivation
curl -s -b "$TOKEN" "$URL/api/invoices" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))"   # expect 5000
```

### Real problems hit deploying this one, and the actual fixes

These are already fixed in the committed `Dockerfile`/`deploy/terraform/run.tf` — listed here so
the *reason* for each isn't a mystery later:

| Symptom | Real cause | Fix |
|---|---|---|
| `pip install torch` pulled ~300MB of unused `nvidia-cuda-*`/`triton` packages, filling the build host's disk | A plain `pip install torch` resolves the full CUDA/GPU build by default, even with no GPU anywhere | Install from the CPU wheel index explicitly: `pip install torch --index-url https://download.pytorch.org/whl/cpu` |
| Revision never went healthy; Cloud Run logs showed a Hugging Face `429` and a 260s forced wait | `sentence-transformers/all-MiniLM-L6-v2` was fetched over the network on every cold start (never cached into the image), and got rate-limited | Pre-download the model at build time: `RUN python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"` |
| Revision still failed health checks even after the fix above | Default Cloud Run startup probe window (~4 min) isn't enough for schema + security + a 5,000-row data scale-up + Pinecone ingestion all running before `uvicorn` ever starts | An explicit, generous `startup_probe` block in `run.tf` (TCP on 8080, `period_seconds = 30`, `failure_threshold = 20`) |
| `Error: ... container ran out of memory` | Cloud Run's default memory (512Mi) isn't enough for PyTorch + the loaded model + an in-memory batch of the data generation all at once | An explicit `resources { limits = { memory = "2Gi", cpu = "2" } }` block in `run.tf` |
| Revision went healthy and served traffic fine, but the **Dashboard page showed 0 for every KPI** (booking requests pending, invoices awaiting review, on hold, approved amount), even after a hard refresh | Three compounding bugs, found by actually loading the dashboard against the real 5,000-invoice deployment: (1) `attach_decisions()` ran one SQL query **per invoice** to fetch its decision history — a real N+1 bug, invisible at a few dozen rows, a multi-minute hang at 5,000 against `db-f1-micro`; (2) no response compression anywhere (the full invoice list is 1.6MB uncompressed); (3) `dashboard.html` downloaded the *entire* invoices/shipmentRequests tables just to compute 4 summary numbers, with **zero error handling** — a slow/failed fetch left every tile silently stuck at its HTML default, with no sign anything had failed | Batched the decisions query into one `WHERE invoice_id = ANY(:ids)` instead of one-per-row (0.3s instead of hanging); added `GZipMiddleware`; added a real `GET /api/dashboard-summary` endpoint (counts/sums computed in SQL, not downloaded row-by-row); wrapped the dashboard's fetch in `try/catch` so a future failure shows `—` instead of a silently-wrong `0` |
| A cold start still took up to **18 minutes**, even after the model was baked into the image — Cloud Run logs showed the same HF Hub `429` and forced wait, twice, on two separate deploys | Baking the model in isn't enough by itself: `sentence-transformers`/`huggingface_hub` still makes a network **HEAD** request at runtime to check for an optional adapter config file, even when the model is fully cached locally | `ENV HF_HUB_OFFLINE=1` in the `Dockerfile`, set *after* the build-time download step (the download itself still needs real network access — offline mode set too early just makes it fail outright). Confirmed with a fresh container restart: zero Hugging Face log lines at all afterward |
| `terraform destroy` refused outright: `cannot destroy service without setting deletion_protection=false` | `google_cloud_run_v2_service` defaults to `deletion_protection = true` in this provider version — never set explicitly in either project's `run.tf` | Add `deletion_protection = false` to the resource, `terraform apply` once to update that one attribute in place, *then* destroy |

This table exists because every one of these was a real, reproducible failure caught by actually
loading the deployed app and clicking around, or actually tearing it down — not something
`terraform plan` or a code read would have caught. If you ever see any of these six again — on a
fresh project, a different region, a rebuilt image — this table is the actual diagnosis, not a new
mystery to debug from scratch.

**The lesson worth keeping, generally: deploying a demo at a "real" data volume is itself a test.**
Everything in this table was invisible at the old ~100-row seed scale and only surfaced once the
dataset was deliberately scaled to 5,000 invoices — exactly the kind of bug a toy dataset can never
catch.

---

## 3. Redeploying after a code change

Both scripts are safe to re-run. Terraform only recreates what changed; `setup_gcp.sh` always
tags the image with a timestamp (never `:latest`), specifically so Cloud Run reliably picks up a
rebuilt image — a fixed tag would otherwise look unchanged to Terraform and silently keep serving
the old revision.

```bash
cd "Northstar-Legacy-System" && bash deploy/setup_gcp.sh YOUR_PROJECT_ID      # or:
cd "Northstar-Legacy-With-AI" && bash deploy/setup_gcp.sh YOUR_PROJECT_ID
```

---

## 4. Teardown

**Order matters here too, in reverse.** Because `Legacy-With-AI` only *reads* `Legacy-System`'s
Cloud SQL instance and secrets (Terraform data sources, never resources it owns), the two
deployments' states can never conflict — but `Legacy-System`'s own full teardown would still
delete the database `Legacy-With-AI` depends on. If both are ever torn down together, destroy
`Legacy-With-AI` first (it owns nothing the other side needs), then `Legacy-System`.

### One-time prerequisite: `deletion_protection`

`google_cloud_run_v2_service` defaults to `deletion_protection = true` in this provider version.
Neither project's `run.tf` set it explicitly at first, so the very first teardown attempt failed
outright with `cannot destroy service without setting deletion_protection=false`. Both `run.tf`
files now set it to `false`, so this step is only needed if you're working from an older checkout:

```bash
cd "Northstar-Legacy-System"   # or Northstar-Legacy-With-AI
terraform -chdir=deploy/terraform apply -target=google_cloud_run_v2_service.app \
  -var="project_id=YOUR_PROJECT_ID" -var="region=us-central1" -auto-approve
```

### Targeted teardown — tear down Legacy-System's own resources, keep the shared DB/secrets

This is the actual teardown run in this project: Legacy-System's own Cloud Run service, service
account, and Artifact Registry repo removed, while the Cloud SQL instance and the 3 shared secrets
(which `Legacy-With-AI` still depends on) are deliberately left untouched.

```bash
cd "Northstar-Legacy-System"

# Preview first — always. Targeting the service account and the Artifact Registry
# repo is enough: Cloud Run's own IAM binding and the IAM grants tied to that
# service account all cascade in as dependents, so you don't need to list them too.
terraform -chdir=deploy/terraform plan -destroy \
  -target=google_service_account.app \
  -target=google_artifact_registry_repository.app \
  -var="project_id=YOUR_PROJECT_ID" -var="region=us-central1"
# -> 8 resources in the preview (the two targets + 6 cascaded dependents, including
#    the Cloud Run service itself)

# Real run
terraform -chdir=deploy/terraform destroy \
  -target=google_service_account.app \
  -target=google_artifact_registry_repository.app \
  -var="project_id=YOUR_PROJECT_ID" -var="region=us-central1" -auto-approve
# -> 6 destroyed (2 had already cascaded out during the apply step above)
```

```bash
# Verify: Legacy-System's own service/repo are gone...
gcloud run services list --platform=managed
gcloud artifacts repositories list

# ...but the shared Cloud SQL instance and secrets Legacy-With-AI depends on survived
gcloud sql instances list                 # northstar-web-db still present
gcloud secrets list                       # db-admin-password, app-role-password,
                                           # fde-role-password still present
```

This is exactly why `data.tf` matters (see §2's intro): a resource Terraform owns gets destroyed
by name; a data source is never a candidate for destruction at all, because the state that ran
this destroy never claimed to own it in the first place.

### Full teardown — both projects, nothing shared left behind

Only do this once nothing is still reading the shared Cloud SQL instance/secrets, i.e. after
`Legacy-With-AI` is already torn down (or never deployed):

```bash
# 1. Legacy-With-AI first — it only reads shared resources, never owns any
cd "Northstar-Legacy-With-AI"
terraform -chdir=deploy/terraform destroy \
  -var="project_id=YOUR_PROJECT_ID" -var="region=us-central1" -auto-approve

# 2. Legacy-System last — safe now that nothing else depends on its DB/secrets
cd "../Northstar-Legacy-System"
terraform -chdir=deploy/terraform destroy \
  -var="project_id=YOUR_PROJECT_ID" -var="region=us-central1" -auto-approve
```

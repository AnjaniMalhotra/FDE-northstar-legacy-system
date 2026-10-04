# One image serves the portal AND the AI copilot — one process, one port
# (see backend/northstar_web_api/main.py, which mounts the AI's own routes
# and the static frontend onto the same FastAPI app).
FROM python:3.12-slim

# ------------------------------------------
# SYSTEM DEPS — psql client, used by backend/scripts/bootstrap.sh
# ------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ------------------------------------------
# PYTHON DEPS — installed before copying app code so this layer stays
# cached across code changes. Heavier than Northstar-Legacy-System's own
# image: sentence-transformers (local RAG embeddings) pulls in PyTorch.
# CPU-only build, installed first and pinned to the CPU wheel index — a
# plain `pip install torch` resolves the full CUDA/GPU build by default
# (several hundred extra MB of nvidia-cuda-*/triton packages this container,
# with no GPU, will never use).
# ------------------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

# ------------------------------------------
# PRE-DOWNLOAD THE EMBEDDING MODEL — baked into the image at build time,
# not fetched from Hugging Face on every cold start. Found the hard way:
# a real Cloud Run deploy failed its startup health check because the
# model download got rate-limited (HF Hub 429) and the forced backoff wait
# alone blew past the startup probe window, before bootstrap.sh's
# "RAG ingestion" step even got to ingest anything.
#
# Baking the model in isn't enough by itself, also found the hard way:
# sentence-transformers/huggingface_hub still makes a HEAD request at
# *runtime* to check for an optional adapter config, even when the model
# is fully cached locally — and that HEAD request is exactly what kept
# getting rate-limited, on every cold start, regardless of the cache.
# HF_HUB_OFFLINE stops it from ever touching the network for this at all —
# set AFTER the download below, not before: the first download still needs
# real network access, offline mode would just make it fail outright.
# ------------------------------------------
RUN python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"
ENV HF_HUB_OFFLINE=1

# ------------------------------------------
# APP CODE
# ------------------------------------------
COPY backend/ backend/
COPY frontend/ frontend/
COPY copilot/ copilot/
COPY data/ data/
COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh backend/scripts/bootstrap.sh

# ------------------------------------------
# RUN — Cloud Run sets $PORT; docker-compose leaves it at the default 8080
# ------------------------------------------
EXPOSE 8080
ENTRYPOINT ["./docker-entrypoint.sh"]

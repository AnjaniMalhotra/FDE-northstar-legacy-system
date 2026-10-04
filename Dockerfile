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

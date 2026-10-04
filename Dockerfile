# One image serves both the API and the static site (see backend/northstar_web_api/main.py) —
# no separate frontend build step, since the site is plain HTML/CSS/JS.
FROM python:3.12-slim

# ------------------------------------------
# SYSTEM DEPS — psql client, used by backend/scripts/bootstrap.sh
# ------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ------------------------------------------
# PYTHON DEPS — installed before copying app code so this layer stays
# cached across code changes
# ------------------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ------------------------------------------
# APP CODE
# ------------------------------------------
COPY backend/ backend/
COPY frontend/ frontend/
COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh backend/scripts/bootstrap.sh

# ------------------------------------------
# RUN — Cloud Run sets $PORT; docker-compose leaves it at the default 8080
# ------------------------------------------
EXPOSE 8080
ENTRYPOINT ["./docker-entrypoint.sh"]

"""
The one database connection this API uses — the northstar_web_app role,
read/write, on the northstar_web database (this project's only one, since
legacy_web/northstar_freight were retired).
"""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import MetaData, create_engine

# ------------------------------------------
# LOAD ENV VARS — read .env from project root for DB credentials
# ------------------------------------------
project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(project_root / ".env")

db_name = os.getenv("NORTHSTAR_WEB_DB_NAME", "northstar_web")
app_password = quote_plus(os.getenv("NORTHSTAR_WEB_APP_PASSWORD", ""))

# ------------------------------------------
# BUILD DATABASE ENGINE — the app's own read/write role, never the admin
# login. Two connection shapes, picked by which env vars are set:
#   - INSTANCE_CONNECTION_NAME set (Cloud Run + Cloud SQL): connect over the
#     Unix socket Cloud Run's built-in Cloud SQL integration mounts at
#     /cloudsql/<INSTANCE_CONNECTION_NAME> — no host/port, no Auth Proxy.
#   - otherwise: plain TCP to DB_HOST:DB_PORT — localhost for local
#     Postgres, or 127.0.0.1 for the Cloud SQL Auth Proxy.
# ------------------------------------------
instance_connection_name = os.getenv("INSTANCE_CONNECTION_NAME")
if instance_connection_name:
    socket_path = f"/cloudsql/{instance_connection_name}"
    db_url = f"postgresql+psycopg://northstar_web_app:{app_password}@/{db_name}?host={socket_path}"
else:
    db_url = (
        f"postgresql+psycopg://northstar_web_app:{app_password}"
        f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{db_name}"
    )
engine = create_engine(db_url)

# ------------------------------------------
# REFLECT TABLES — read the schema from the live database instead of
# redeclaring every column in Python; scripts/northstar_web_schema.sql is
# the one place table structure is defined.
# ------------------------------------------
metadata = MetaData()
metadata.reflect(bind=engine)


# ------------------------------------------
# PER-REQUEST CONNECTION — one transaction per request, committed on success
# ------------------------------------------
def get_conn():
    with engine.begin() as conn:
        yield conn

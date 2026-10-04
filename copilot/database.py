"""The restricted database connection shared by application modules."""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine


# ------------------------------------------
# LOAD ENV VARS — read .env from project root for DB credentials
# ------------------------------------------
project_root = Path(__file__).resolve().parent.parent
load_dotenv(project_root / ".env")

# ------------------------------------------
# BUILD DATABASE ENGINE — restricted agent connection to Postgres. Two
# connection shapes, picked by whether INSTANCE_CONNECTION_NAME is set —
# same branch backend/northstar_web_api/db.py uses, so this resolves
# correctly whether it's running locally or on Cloud Run.
# ------------------------------------------
agent_user = os.getenv("DB_AGENT_USER")
agent_password = os.getenv("DB_AGENT_PASSWORD")
db_name = os.getenv("DB_NAME")
instance_connection_name = os.getenv("INSTANCE_CONNECTION_NAME")
if instance_connection_name:
    socket_path = f"/cloudsql/{instance_connection_name}"
    db_url = f"postgresql+psycopg://{agent_user}:{agent_password}@/{db_name}?host={socket_path}"
else:
    db_url = (
        f"postgresql+psycopg://{agent_user}:{agent_password}"
        f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{db_name}"
    )
engine = create_engine(db_url)

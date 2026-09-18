"""
The one database connection this API uses — the northstar_web_app role,
read/write, on the northstar_web database (this project's only one, since
legacy_web/northstar_freight were retired — see
docs/build-log/06-retire-legacy-web-and-northstar-freight.md).
"""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import MetaData, create_engine

# ------------------------------------------
# LOAD ENV VARS — read .env from project root for DB credentials
# ------------------------------------------
project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(project_root / ".env")

db_name = os.getenv("NORTHSTAR_WEB_DB_NAME", "northstar_web")

# ------------------------------------------
# BUILD DATABASE ENGINE — the app's own read/write role, never the admin login
# ------------------------------------------
engine = create_engine(
    f"postgresql+psycopg://northstar_web_app:{os.getenv('NORTHSTAR_WEB_APP_PASSWORD')}"
    f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{db_name}"
)

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

"""The one admin database connection shared by every legacy_web route.

This predates any concept of a restricted AI role — it's Northstar's own
internal tooling, used by staff with full access to their own data. There
is no "agent" here at all (mirrors src/legacy_ui.py's same choice).
"""
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
project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(project_root / ".env")

# ------------------------------------------
# ADMIN DATABASE ENGINE — full-access connection, no restricted AI role here
# ------------------------------------------
admin_engine = create_engine(
    f"postgresql+psycopg://{os.getenv('DB_ADMIN_USER')}:{os.getenv('DB_ADMIN_PASSWORD')}"
    f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME')}"
)

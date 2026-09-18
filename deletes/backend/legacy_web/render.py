"""The one shared Jinja2 template environment, used by every route file."""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
from pathlib import Path

from fastapi.templating import Jinja2Templates

# ------------------------------------------
# TEMPLATE ENVIRONMENT — points at backend/legacy_web/templates/
# ------------------------------------------
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))

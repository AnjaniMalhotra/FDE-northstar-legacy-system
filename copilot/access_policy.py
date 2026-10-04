"""
The single source of truth for what each role can read, write, see, and ask
the AI to do — data/policy/access_policy.json. Nothing in the UI or the
agent's tools should hardcode a role check; they call into this module
instead, so a new rule means editing one JSON file, not hunting through
scattered `if role == ...` blocks.

The database GRANTs (scripts/northstar_web_ai_security.sql) remain the
actual enforcement for data access — this file documents that same
boundary for display, and is the real enforcement for two things that had
no gate before: which UI tabs a role sees, and which AI tools a role's
agent session may use.
"""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# ------------------------------------------
# LOAD .env — this module reads POC_DEMO_STAGE at import time (below), so
# .env has to be loaded here rather than assumed already loaded by whichever
# other module happens to be imported first (same pattern as database.py,
# identity.py, orchestrator.py).
# ------------------------------------------
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# ------------------------------------------
# POLICY FILE PATH — location of access_policy.json
# ------------------------------------------
POLICY_PATH = Path(__file__).resolve().parent.parent / "data" / "policy" / "access_policy.json"

# ------------------------------------------
# POC DEMO STAGE — which tabs are visible in this course role-play, not a
# real permission. PART_1 is what the FDE first pitched the client (detention
# + linehaul verification, audit log); PART_2 (default) adds Pending
# Approvals, built after the client's checkpoint feedback. A table, not a
# hardcoded `if`, so a future stage is a new dict entry, not new branching
# code.
# ------------------------------------------
DEMO_STAGE = os.getenv("POC_DEMO_STAGE", "PART_2")
STAGE_HIDDEN_TABS = {"PART_1": {"approvals"}}


# ------------------------------------------
# ROLE PERMISSIONS SCHEMA — one record per role's data/UI/tool access
# ------------------------------------------
@dataclass(frozen=True)
class RolePermissions:
    role: str
    description: str
    data_read: list[str]
    data_write: list[str]
    ui_tabs: list[str]
    ai_tools: list[str]


# ------------------------------------------
# LOAD POLICY FROM JSON — parses access_policy.json into RolePermissions objects
# ------------------------------------------
def _load() -> dict[str, RolePermissions]:
    config = json.loads(POLICY_PATH.read_text())
    return {role: RolePermissions(role=role, **fields) for role, fields in config.items()}


# ------------------------------------------
# LOAD PERMISSIONS ONCE AT IMPORT — cached in-memory policy table
# ------------------------------------------
_PERMISSIONS = _load()


# ------------------------------------------
# GET PERMISSIONS — look up a role's permissions, error on unknown role
# ------------------------------------------
def get_permissions(role: str) -> RolePermissions:
    if role not in _PERMISSIONS:
        raise ValueError(f"Unknown role: {role}")
    return _PERMISSIONS[role]


# ------------------------------------------
# VISIBLE TABS — a role's ui_tabs, minus whatever this demo stage hides
# ------------------------------------------
def visible_tabs(role: str) -> list[str]:
    hidden = STAGE_HIDDEN_TABS.get(DEMO_STAGE, set())
    return [t for t in get_permissions(role).ui_tabs if t not in hidden]


# ------------------------------------------
# CHECK UI TAB ACCESS — whether a role can see a given UI tab, at this stage
# ------------------------------------------
def can_view_tab(role: str, tab_key: str) -> bool:
    return tab_key in visible_tabs(role)


# ------------------------------------------
# CHECK AI TOOL ACCESS — whether a role can use a given AI tool
# ------------------------------------------
def can_use_ai_tool(role: str, tool_name: str) -> bool:
    return tool_name in get_permissions(role).ai_tools


# ------------------------------------------
# DESCRIBE ACCESS — plain-language summary for the UI's My Access panel
# ------------------------------------------
def describe(role: str) -> str:
    """Plain-language block for the UI's 'My Access' panel."""
    p = get_permissions(role)
    lines = [
        p.description,
        "",
        f"**Data you can read:** {', '.join(p.data_read)}",
        f"**Data you can write:** {', '.join(p.data_write) if p.data_write else 'none — read-only'}",
        f"**What you can ask the AI to do:** {', '.join(p.ai_tools)}",
    ]
    return "\n\n".join(lines)

"""Redact sensitive-looking content and write it to the structured audit log.
Split out of orchestrator.py so "how a turn is wired" and "how a turn gets
logged" can be read as two separate, shorter questions.
"""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
import json
import re

from sqlalchemy import text

from copilot.database import engine

# ------------------------------------------
# REDACTION PATTERNS — sensitive-looking content to strip before it hits the audit log
# ------------------------------------------
# Patterns for content that should never sit in a plaintext audit log,
# even though nothing in Northstar's current schema actually produces them
# yet (no bank/routing numbers, no card numbers anywhere in this project).
# This is a real, tested no-op today, kept as a genuine safety net for the
# day a tool starts returning something it shouldn't — not defensive code
# for a scenario the codebase invents to look thorough.
_REDACTION_PATTERNS = [
    (re.compile(r"\b\d{9}\b"), "[REDACTED-ROUTING-NUMBER]"),          # US bank routing numbers
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "[REDACTED-CARD-NUMBER]"),  # card-like digit runs
]


# ------------------------------------------
# REDACT — apply every redaction pattern to a piece of content
# ------------------------------------------
def redact(content: str) -> str:
    for pattern, replacement in _REDACTION_PATTERNS:
        content = pattern.sub(replacement, content)
    return content


# ------------------------------------------
# WRITE AUDIT LOG — insert-only trace row, redacted and truncated, non-fatal on failure
# ------------------------------------------
def write_audit_log(
    session_id: str, node_name: str, tool_name: str, content: str,
    trace_id: str = "", role: str = "", latency_ms: int = 0, metadata: dict | None = None,
) -> None:
    """Appends one structured trace row (Evidence Pack material, Phase 6).
    trace_id ties every step of one user turn together; role records who
    asked. Content is redacted before storage (see redact() above) and
    truncated to 2000 chars. Uses the agent's own restricted connection —
    northstar_web_agent can INSERT here but can never read it back or modify
    it (see scripts/northstar_web_ai_security.sql). A logging failure should
    never crash the agent turn, so it's caught and printed, not raised."""
    insert = text("""
        INSERT INTO agent_audit_log
            (session_id, node_name, tool_name, content, trace_id, role, latency_ms, metadata)
        VALUES (:session_id, :node_name, :tool_name, :content, :trace_id, :role, :latency_ms, :metadata)
    """)
    try:
        with engine.begin() as conn:
            conn.execute(insert, {
                "session_id": session_id, "node_name": node_name,
                "tool_name": tool_name, "content": redact(content)[:2000],
                "trace_id": trace_id, "role": role, "latency_ms": latency_ms,
                "metadata": json.dumps(metadata or {}),
            })
    except Exception as e:
        print(f"  [audit log write failed, non-fatal: {e}]")

"""
Request-scoped state shared between the orchestrator and the tools it
calls — specifically the "was real policy evidence retrieved this turn"
flag that log_dispute_flag checks before it will write anything.

This was originally built on contextvars.ContextVar, which turned out to be
the wrong tool: LangGraph's ToolNode runs tools via a ThreadPoolExecutor, and
ContextVar does NOT propagate into a new thread started that way (verified
directly — a value set in the main thread read back as its default inside a
worker thread). The correct mechanism is a tool parameter type-hinted as
RunnableConfig — LangChain auto-injects the real run config into it, hidden
from the LLM's tool schema, and config DOES correctly carry values like
thread_id across that same thread-pool boundary (also verified directly).
So: orchestrator.py puts trace_id/role into the graph config it already
passes on every call; tools that need them declare a `config: RunnableConfig`
parameter and read it from there. This module holds only the one piece of
state that can't just be read from config — a shared, keyed record of which
trace_ids have seen real policy evidence, since it has to be set by one tool
call and read by a later, separate one.
"""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
import threading

# ------------------------------------------
# MODULE STATE — lock-guarded map of trace_id to "policy evidence seen this turn"
# ------------------------------------------
_lock = threading.Lock()
_evidence_by_trace: dict[str, bool] = {}


# ------------------------------------------
# MARK POLICY EVIDENCE OK — record that this trace retrieved real policy evidence
# ------------------------------------------
def mark_policy_evidence_ok(trace_id: str) -> None:
    if not trace_id:
        return
    with _lock:
        _evidence_by_trace[trace_id] = True


# ------------------------------------------
# CHECK POLICY EVIDENCE — whether this trace has seen policy evidence yet
# ------------------------------------------
def has_policy_evidence(trace_id: str) -> bool:
    with _lock:
        return _evidence_by_trace.get(trace_id, False)


# ------------------------------------------
# CLEAR TRACE — remove a finished turn's entry so the dict doesn't grow unbounded
# ------------------------------------------
def clear_trace(trace_id: str) -> None:
    """Called once the turn is over, so this dict doesn't grow unbounded
    across a long-running server process."""
    with _lock:
        _evidence_by_trace.pop(trace_id, None)

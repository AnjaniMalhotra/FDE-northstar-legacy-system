"""Run one turn through the agent, streaming its steps and audit-logging
each one under a shared trace_id. Split out of orchestrator.py so "how the
agent is wired" and "how you actually run a turn through it" are two
separate, shorter files.
"""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
import time
import uuid

from copilot.audit_logging import write_audit_log
from copilot.orchestrator import load_system_prompt, northstar_agent
from copilot.tracing import clear_trace


# ------------------------------------------
# ASK — stream one turn through the agent, printing and audit-logging as it goes
# ------------------------------------------
def ask(question: str, thread_config: dict, role: str = "ANALYST") -> str:
    """Streams one turn through the agent, printing and audit-logging every
    tool call and the final response under one shared trace_id. Shared by
    the interactive loop below and scripts/test_agent_queries.py, so both
    get identical logging.

    trace_id/role are merged into the SAME config passed to the graph, so
    any tool that declares a `config: RunnableConfig` parameter (see
    search_policy_documents in copilot/tools/policy_tools.py, log_dispute_flag
    in copilot/tools/flag_tools.py) receives them automatically — this is
    what lets log_dispute_flag write its own atomic audit event from inside
    a ToolNode worker thread. See copilot/tracing.py for why this replaced
    an earlier, broken contextvars approach."""
    # ------------------------------------------
    # SET UP THE TURN — one shared trace_id, merged into the graph's run config
    # ------------------------------------------
    session_id = thread_config["configurable"]["thread_id"]
    trace_id = str(uuid.uuid4())
    run_config = {"configurable": {**thread_config["configurable"], "trace_id": trace_id, "role": role}}
    final_response = ""
    step_started = time.monotonic()

    try:
        # ------------------------------------------
        # STREAM THE GRAPH — run the reasoner/tools loop, one update event at a time
        # ------------------------------------------
        events = northstar_agent.stream(
            {"messages": [("user", question)]}, config=run_config, stream_mode="updates"
        )
        for event in events:
            for node_name, node_state in event.items():
                latency_ms = int((time.monotonic() - step_started) * 1000)
                step_started = time.monotonic()

                # ------------------------------------------
                # TOOLS NODE — log each tool call's result (log_dispute_flag logs itself)
                # ------------------------------------------
                if node_name == "tools":
                    for msg in node_state["messages"]:
                        print(f"  [tool: {msg.name}]")
                        step_metadata = {"abstained": "ABSTAIN" in str(msg.content)} if msg.name == "search_policy_documents" else {}
                        # log_dispute_flag already wrote its own atomic audit
                        # event (see copilot/tools/flag_tools.py) — logging it
                        # again here would duplicate that row, not add safety.
                        if msg.name != "log_dispute_flag":
                            write_audit_log(session_id, "tools", msg.name, str(msg.content),
                                             trace_id=trace_id, role=role, latency_ms=latency_ms, metadata=step_metadata)
                # ------------------------------------------
                # REASONER NODE — capture and log the final response, once produced
                # ------------------------------------------
                elif node_name == "reasoner":
                    latest = node_state["messages"][-1]
                    if latest.content:
                        final_response = latest.content
                        print(f"\nAgent:\n{latest.content}\n")
                        write_audit_log(session_id, "reasoner", "final_response", latest.content,
                                         trace_id=trace_id, role=role, latency_ms=latency_ms)
        return final_response
    finally:
        # ------------------------------------------
        # CLEAR TRACE — drop this turn's policy-evidence flag once the turn is over
        # ------------------------------------------
        clear_trace(trace_id)


# ------------------------------------------
# INTERACTIVE LOOP — run this file directly for a command-line chat session
# ------------------------------------------
if __name__ == "__main__":
    thread_config = {"configurable": {"thread_id": "interactive-session"}}
    northstar_agent.invoke({"messages": [load_system_prompt()]}, config=thread_config)

    print("Northstar Freight reconciliation agent. Type 'exit' to quit.\n")
    while True:
        user_input = input("Analyst > ")
        if user_input.lower() in ("exit", "quit"):
            break
        ask(user_input, thread_config)

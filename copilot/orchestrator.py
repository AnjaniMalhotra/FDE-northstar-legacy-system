"""
The Northstar Freight reconciliation agent: a LangGraph state machine with two
nodes — a "reasoner" (the LLM, with tools bound) and a "tools" node that
executes whatever the reasoner asks for — looping between them until the
reasoner produces a final answer instead of another tool call.

The LLM is a local Ollama model by default — no API key, nothing leaves this
machine except the Pinecone vector search inside search_policy_documents (see
CLAUDE.md's note on that one deliberate exception).

This file only builds and compiles the graph. To actually run a turn through
it, see copilot/agent_runner.py's ask().
"""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
import os
import sys
from pathlib import Path
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

# ------------------------------------------
# FIX UP sys.path — so `copilot.*` imports resolve regardless of how this is run
# ------------------------------------------
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# ------------------------------------------
# TOOL IMPORTS — depend on sys.path being fixed up above
# ------------------------------------------
from copilot.tools import (
    check_detention_reconciliation,
    check_linehaul_reconciliation,
    get_carrier_flag_history,
    get_carrier_invoice_history,
    get_carrier_risk_profile,
    get_dispute_flag_summary,
    get_invoice_details,
    get_shipment_status_summary,
    log_dispute_flag,
    query_northstar_data,
    search_policy_documents,
)

# ------------------------------------------
# LOAD ENV VARS
# ------------------------------------------
load_dotenv(project_root / ".env")


# ------------------------------------------
# AGENT STATE — the LangGraph state: an append-only message list
# ------------------------------------------
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# ------------------------------------------
# SELECT LLM PROVIDER — OLLAMA (default, local) or OPENAI (the one cloud exception)
# ------------------------------------------
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "OLLAMA").strip().upper()

if LLM_PROVIDER == "OPENAI":
    from langchain_openai import ChatOpenAI
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    print(f"Reasoning LLM: OpenAI ({OPENAI_MODEL}) — the one deliberate cloud exception alongside Pinecone.")
    llm = ChatOpenAI(model=OPENAI_MODEL, temperature=0)
else:
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    print(f"Reasoning LLM: local Ollama ({OLLAMA_MODEL}).")
    llm = ChatOllama(model=OLLAMA_MODEL, temperature=0)

# ------------------------------------------
# BIND TOOLS TO THE LLM — the tools the reasoner node is allowed to call
# ------------------------------------------
northstar_tools = [
    check_detention_reconciliation,
    check_linehaul_reconciliation,
    get_invoice_details,
    search_policy_documents,
    get_carrier_invoice_history,
    get_carrier_flag_history,
    get_carrier_risk_profile,
    query_northstar_data,
    log_dispute_flag,
    get_dispute_flag_summary,
    get_shipment_status_summary,
]
llm_with_tools = llm.bind_tools(northstar_tools)


# ------------------------------------------
# REASONING NODE — the LLM step: read messages, produce a reply or a tool call
# ------------------------------------------
def reasoning_node(state: AgentState):
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}


# ------------------------------------------
# BUILD THE GRAPH — reasoner <-> tools loop, wired with a conditional edge
# ------------------------------------------
graph_builder = StateGraph(AgentState)
graph_builder.add_node("reasoner", reasoning_node)
graph_builder.add_node("tools", ToolNode(northstar_tools))
graph_builder.add_edge(START, "reasoner")
graph_builder.add_conditional_edges("reasoner", tools_condition)
graph_builder.add_edge("tools", "reasoner")

northstar_agent = graph_builder.compile(checkpointer=InMemorySaver())


# ------------------------------------------
# LOAD SYSTEM PROMPT — read the agent's instructions from copilot/prompts/system_prompt.txt
# ------------------------------------------
def load_system_prompt() -> SystemMessage:
    prompt_path = project_root / "copilot" / "prompts" / "system_prompt.txt"
    return SystemMessage(content=prompt_path.read_text(encoding="utf-8"))

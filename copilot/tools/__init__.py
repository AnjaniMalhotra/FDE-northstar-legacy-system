"""
Tools for the Northstar Freight reconciliation agent, split by concern
(sql_tools, carrier_tools, reconciliation_tools, policy_tools,
summary_tools, flag_tools) — each a thin wrapper around something already
built and tested elsewhere, or a direct read-only database connection.
This file just re-exports the public surface so callers don't need to know
the internal layout.
"""
# ------------------------------------------
# IMPORTS — re-export the per-concern tool modules' public surface
# ------------------------------------------
from copilot.database import engine

from copilot.tools.carrier_tools import (
    get_carrier_flag_history,
    get_carrier_invoice_history,
    get_carrier_risk_profile,
)
from copilot.tools.flag_tools import log_dispute_flag
from copilot.tools.policy_tools import RELEVANCE_THRESHOLD, _embedding_model, _policy_index, search_policy_documents
from copilot.tools.reconciliation_tools import check_detention_reconciliation, check_linehaul_reconciliation, get_invoice_details
from copilot.tools.summary_tools import get_dispute_flag_summary, get_shipment_status_summary
from copilot.tools.sql_tools import query_northstar_data

# ------------------------------------------
# ALL_TOOLS — the list handed to the agent so it knows what it can call
# ------------------------------------------
ALL_TOOLS = [
    query_northstar_data,
    get_carrier_invoice_history,
    get_carrier_flag_history,
    get_carrier_risk_profile,
    check_detention_reconciliation,
    check_linehaul_reconciliation,
    get_invoice_details,
    search_policy_documents,
    log_dispute_flag,
    get_dispute_flag_summary,
    get_shipment_status_summary,
]

# ------------------------------------------
# __all__ — the module's public export list
# ------------------------------------------
__all__ = [
    "engine", "RELEVANCE_THRESHOLD", "_embedding_model", "_policy_index",
    "query_northstar_data", "get_carrier_invoice_history", "get_carrier_flag_history",
    "get_carrier_risk_profile", "check_detention_reconciliation",
    "check_linehaul_reconciliation", "get_invoice_details", "search_policy_documents",
    "log_dispute_flag", "get_dispute_flag_summary", "get_shipment_status_summary",
    "ALL_TOOLS",
]

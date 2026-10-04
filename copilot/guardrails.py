"""Inspectable policy checks for dispute-flag authorization.

The agent never supplies reconciliation values to this module. It receives
database-derived facts from copilot.reconciliation_detention /
copilot.reconciliation_linehaul and applies the policy in two visible
stages: verified-discrepancy eligibility, then escalation tier.

Both Tier 2 triggers named in the policy document (Section 3-4) are
implemented here: the dollar threshold and the repeat-flag-count pattern.
(Two earlier triggers — 2+ upheld disputes, and carrier Elevated Risk
status — were removed along with the Carrier Risk & Disputes console tab
that was the only way to ever set either one.)

Thresholds live in copilot.dispute_policy; plain-language translations of the
result live in copilot.plain_language — this file is just the decision pipeline.
"""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.engine import Engine

from copilot.dispute_policy import DisputePolicy, POLICY
from copilot.reconciliation_detention import Reconciliation
from copilot.reconciliation_linehaul import LinehaulReconciliation


# ------------------------------------------
# AUTHORIZATION RESULT — the tier/decision produced by a policy check
# ------------------------------------------
@dataclass(frozen=True)
class AuthorizationResult:
    tier: str | None
    can_auto_log: bool
    reason: str
    is_flaggable: bool
    policy_version: str = ""  # which version of DisputePolicy produced this decision — recorded in every audit trace


# ------------------------------------------
# VERIFIED DISCREPANCY — Section 2 eligibility check (is this even flaggable)
# ------------------------------------------
def verified_discrepancy(result: Reconciliation, policy: DisputePolicy = POLICY) -> AuthorizationResult:
    """Apply Section 2. A dispute flag concerns an overbilled charge only."""
    failed_rules = []
    if result.amount_variance <= Decimal("0"):
        failed_rules.append("the billed amount is not greater than the actual amount")
    if result.time_variance <= policy.minimum_time_variance:
        failed_rules.append(f"time variance is not more than {policy.minimum_time_variance.seconds // 60} minutes")
    if result.amount_variance <= policy.minimum_overcharge:
        failed_rules.append(f"overcharge is not more than ${policy.minimum_overcharge:.2f}")
    if failed_rules:
        return AuthorizationResult(None, False, f"Not logged — Section 2 requires a verified discrepancy; {'; '.join(failed_rules)}.", False, policy.version)
    return AuthorizationResult("TIER_1", True, "Section 2 verified discrepancy requirements are met.", True, policy.version)


# ------------------------------------------
# VERIFIED LINEHAUL DISCREPANCY — dollar-only eligibility (no time dimension)
# ------------------------------------------
def verified_linehaul_discrepancy(result: LinehaulReconciliation, policy: DisputePolicy = POLICY) -> AuthorizationResult:
    """Linehaul has no dwell-time concept — it's a flat agreed-vs-billed rate
    check, so only the dollar-overcharge rule from Section 2 applies (see
    data/policy/linehaul_rate_policy.md)."""
    failed_rules = []
    if result.amount_variance <= Decimal("0"):
        failed_rules.append("the billed amount is not greater than the agreed rate")
    if result.amount_variance <= policy.minimum_overcharge:
        failed_rules.append(f"overcharge is not more than ${policy.minimum_overcharge:.2f}")
    if failed_rules:
        return AuthorizationResult(None, False, f"Not logged — a verified linehaul discrepancy requires: {'; '.join(failed_rules)}.", False, policy.version)
    return AuthorizationResult("TIER_1", True, "Linehaul verified discrepancy requirements are met.", True, policy.version)


# ------------------------------------------
# RECENT FLAG COUNT — Section 4 trigger: all flags for this carrier in the window
# ------------------------------------------
def recent_flag_count(engine: Engine, carrier_id: int, policy: DisputePolicy = POLICY) -> int:
    """Section 4's trigger: ALL flags in the window count, regardless of how
    they were later resolved — a pattern of small discrepancies is itself
    a signal, even before any of them are confirmed as real fraud."""
    query = text("""
        SELECT COUNT(*) FROM dispute_flags
        WHERE carrier_id = :carrier_id
          AND created_at >= NOW() - (:window_days * INTERVAL '1 day')
    """)
    with engine.connect() as conn:
        return int(conn.execute(query, {"carrier_id": carrier_id, "window_days": policy.repeat_window_days}).scalar_one())


# ------------------------------------------
# TIER VERIFIED DISCREPANCY — Sections 3-4: decide Tier 1 vs. Tier 2 escalation
# ------------------------------------------
def tier_verified_discrepancy(
    result: Reconciliation,
    prior_flag_count: int,
    policy: DisputePolicy = POLICY,
) -> AuthorizationResult:
    """Apply Sections 3–4 after Section 2 has already passed. Checks both
    documented Tier 2 triggers, in the order the policy lists them."""
    if result.amount_variance >= policy.tier_2_overcharge:
        return AuthorizationResult("TIER_2", False, f"Section 3: ${result.amount_variance:.2f} meets the ${policy.tier_2_overcharge:.2f} Tier 2 threshold.", True, policy.version)
    if prior_flag_count >= policy.repeat_flag_count - 1:
        return AuthorizationResult("TIER_2", False, f"Section 4: this would be flag {prior_flag_count + 1} in {policy.repeat_window_days} days, requiring Tier 2 review.", True, policy.version)
    return AuthorizationResult("TIER_1", True, "Sections 3–4: Tier 1; neither Tier 2 trigger applies.", True, policy.version)


# ------------------------------------------
# AUTHORIZE FLAG — the full policy pipeline: eligibility, then tier, all database-derived
# ------------------------------------------
def authorize_flag(engine: Engine, result: Reconciliation, policy: DisputePolicy = POLICY) -> AuthorizationResult:
    """Apply Sections 2–4 to a database-derived reconciliation result. Every
    fact used here is looked up independently — none of it is trusted from
    the caller, including the agent."""
    eligibility = verified_discrepancy(result, policy)
    if not eligibility.is_flaggable:
        return eligibility
    flag_count = recent_flag_count(engine, result.carrier_id, policy)
    return tier_verified_discrepancy(result, flag_count, policy)


# ------------------------------------------
# AUTHORIZE LINEHAUL FLAG — same pipeline as authorize_flag, linehaul eligibility instead
# ------------------------------------------
def authorize_linehaul_flag(engine: Engine, result: LinehaulReconciliation, policy: DisputePolicy = POLICY) -> AuthorizationResult:
    """Mirrors authorize_flag(): eligibility first, then the same
    charge-agnostic tier logic (dollar threshold, repeat pattern) —
    tier_verified_discrepancy only ever reads amount_variance and
    carrier-level facts, so it applies unchanged."""
    eligibility = verified_linehaul_discrepancy(result, policy)
    if not eligibility.is_flaggable:
        return eligibility
    flag_count = recent_flag_count(engine, result.carrier_id, policy)
    return tier_verified_discrepancy(result, flag_count, policy)

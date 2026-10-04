"""Translate a stored flag's tier/reasoning into plain, non-technical
language. A pure presentation transform of already-authoritative text
(dispute_flags.tier_reason) — re-derives nothing and never recomputes a
decision itself.
"""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
import re

from copilot.dispute_policy import DisputePolicy, POLICY


# ------------------------------------------
# PLAIN LANGUAGE OUTCOME — one sentence explaining why a flag needs (or doesn't need) approval
# ------------------------------------------
def plain_language_outcome(tier: str | None, reasoning: str = "") -> str:
    if tier is None:
        return "No problem found — the numbers match what's expected."
    if tier == "TIER_1":
        return "This is a smaller, one-off issue — logged automatically, but still needs your Approve/Hold decision below."
    if "upheld dispute" in reasoning:
        return "This carrier has had confirmed billing disputes recently, so this needs manager approval."
    if "Elevated Risk" in reasoning:
        return "This carrier is marked as higher risk, so every charge from them needs manager approval."
    match = re.search(r"flag (\d+) in (\d+) days", reasoning)
    if match:
        prior = int(match.group(1)) - 1
        return (f"This carrier has had {prior} other billing issue{'s' if prior != 1 else ''} in the last "
                f"{match.group(2)} days, so this one needs manager approval too.")
    match = re.search(r"meets the \$([\d.]+)", reasoning)
    if match:
        return f"This charge is large enough (over ${match.group(1)}) that a manager must approve it, not just an analyst."
    return "This needs manager approval before it can be paid."


# ------------------------------------------
# PLAIN LANGUAGE POLICY LINE — the one rule that decides if something gets a second look
# ------------------------------------------
def plain_language_policy_line(policy: DisputePolicy = POLICY) -> str:
    minutes = policy.minimum_time_variance.seconds // 60
    return (f"Company rule: a detention charge is only questioned if it's off by more than "
            f"{minutes} minutes and ${policy.minimum_overcharge:.2f}.")


# ------------------------------------------
# PLAIN LANGUAGE LINEHAUL POLICY LINE — the linehaul equivalent (no time dimension)
# ------------------------------------------
def plain_language_linehaul_policy_line(policy: DisputePolicy = POLICY) -> str:
    return (f"Company rule: a linehaul charge is only questioned if it's billed more than "
            f"${policy.minimum_overcharge:.2f} over the rate agreed at booking.")

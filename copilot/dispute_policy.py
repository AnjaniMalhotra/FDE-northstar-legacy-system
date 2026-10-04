"""The dispute policy's numeric thresholds — loaded from JSON, not hardcoded.

data/policy/accessorial_dispute_policy.md (what a human reads) and
policy_config.json (what the code enforces) both describe the same numbers;
scripts/test_policy_consistency.py is the automatic tripwire that catches
the two drifting apart.
"""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
import json
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

# ------------------------------------------
# POLICY CONFIG PATH — location of policy_config.json, the single source of truth for thresholds
# ------------------------------------------
POLICY_CONFIG_PATH = Path(__file__).resolve().parent.parent / "data" / "policy" / "policy_config.json"


# ------------------------------------------
# DISPUTE POLICY SCHEMA — the numeric thresholds a flag decision is checked against
# ------------------------------------------
@dataclass(frozen=True)
class DisputePolicy:
    version: str
    effective_date: str
    minimum_time_variance: timedelta
    minimum_overcharge: Decimal
    tier_2_overcharge: Decimal
    repeat_flag_count: int
    repeat_window_days: int


# ------------------------------------------
# LOAD POLICY — read policy_config.json into a DisputePolicy
# ------------------------------------------
def load_policy(path: Path = POLICY_CONFIG_PATH) -> DisputePolicy:
    config = json.loads(path.read_text())
    return DisputePolicy(
        version=config["version"],
        effective_date=config["effective_date"],
        minimum_time_variance=timedelta(minutes=config["minimum_time_variance_minutes"]),
        minimum_overcharge=Decimal(config["minimum_overcharge"]),
        tier_2_overcharge=Decimal(config["tier_2_overcharge"]),
        repeat_flag_count=config["repeat_flag_count"],
        repeat_window_days=config["repeat_window_days"],
    )


# ------------------------------------------
# LOAD POLICY ONCE AT IMPORT — the active DisputePolicy used by default everywhere
# ------------------------------------------
POLICY = load_policy()

"""Derives a human-readable shipment status from real dock events and
appointment times — not a stored field, since nothing in the legacy schema
tracks live status directly."""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
from datetime import datetime


# ------------------------------------------
# COMPUTE STATUS FROM DOCK EVENTS — derive shipment status from arrival/departure and appointment times
# ------------------------------------------
def compute_status(pickup_appt: datetime, delivery_appt: datetime,
                    has_arrival: bool, has_departure: bool, now: datetime) -> str:
    if has_departure:
        return "DELIVERED"
    if has_arrival:
        return "AT_DOCK"
    if pickup_appt > now:
        return "SCHEDULED"
    return "ENROUTE"

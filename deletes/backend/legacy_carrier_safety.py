"""TransCheck — the external carrier-safety registry Northstar doesn't own.

Real freight brokerages check a carrier's safety/compliance record (DOT
out-of-service violations, insurance status) from an outside registry before
trusting them with a load — data that never lives in a company's own Carrier
Master file. That's the one real lesson this module exists to teach: some
data genuinely lives somewhere else, and checking it is an extra step nobody
bothers with unless something's already gone wrong.

Earlier versions of this simulated the "external system" as a real SOAP/XML
service running on its own port — accurate to how this integration would
look in a real company, but a second process to keep running added
operational complexity (a service that could silently go stale) without
teaching anything the plain version below doesn't. This keeps the lesson —
a disconnected data source, looked up through a function, never a direct
database join — and drops the wire protocol.
"""
# ------------------------------------------
# CARRIER SAFETY DATA — in-memory mock of the external registry's dataset
# ------------------------------------------
# Northstar doesn't own or control this data — it's not in Postgres, on
# purpose. Two carriers (the same repeat offenders from the synthetic
# invoice data) have elevated violation counts.
CARRIER_SAFETY_DATA = {
    "MC-100000": {"carrier_name": "Redline Transport", "out_of_service_violations": 1, "insurance_status": "Active"},
    "MC-100001": {"carrier_name": "Bluewave Freight", "out_of_service_violations": 0, "insurance_status": "Active"},
    "MC-100002": {"carrier_name": "Pioneer Haulers", "out_of_service_violations": 5, "insurance_status": "Active"},
    "MC-100003": {"carrier_name": "Summit Trucking", "out_of_service_violations": 1, "insurance_status": "Active"},
    "MC-100004": {"carrier_name": "Coastal Carriers", "out_of_service_violations": 0, "insurance_status": "Active"},
    "MC-100005": {"carrier_name": "Ironhorse Logistics", "out_of_service_violations": 2, "insurance_status": "Active"},
    "MC-100006": {"carrier_name": "Prairie Express", "out_of_service_violations": 6, "insurance_status": "Expired"},
    "MC-100007": {"carrier_name": "Vantage Freightways", "out_of_service_violations": 3, "insurance_status": "Active"},
    "MC-100008": {"carrier_name": "Northbound Transit", "out_of_service_violations": 0, "insurance_status": "Active"},
    "MC-100009": {"carrier_name": "Silver Creek Trucking", "out_of_service_violations": 1, "insurance_status": "Active"},
    "MC-100010": {"carrier_name": "Apex Line Haul", "out_of_service_violations": 0, "insurance_status": "Active"},
    "MC-100011": {"carrier_name": "Cascade Freight Co", "out_of_service_violations": 1, "insurance_status": "Active"},
}


# ------------------------------------------
# GET CARRIER SAFETY PROFILE — the one lookup this "external system" offers
# ------------------------------------------
def get_carrier_safety_profile(mc_number: str) -> dict:
    """Returns {mc_number, carrier_name, out_of_service_violations,
    insurance_status}, or raises ValueError if the MC number is unknown —
    same contract a real external registry call would have, minus the
    network round-trip."""
    profile = CARRIER_SAFETY_DATA.get(mc_number)
    if profile is None:
        raise ValueError(f"Unknown carrier MC number: {mc_number}")
    return {"mc_number": mc_number, **profile}

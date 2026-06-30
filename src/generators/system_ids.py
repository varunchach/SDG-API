"""System-specific ID generators per producer subsystem."""

from __future__ import annotations

import random
import time
import uuid


def _numeric_id(rng: random.Random, length: int = 9) -> str:
    return "".join(str(rng.randint(0, 9)) for _ in range(length))


def generate_orc_journey_id(
    product_name: str,
    rng: random.Random,
    *,
    used: set[str] | None = None,
) -> str:
    used_set = used if used is not None else set()
    for _ in range(100):
        suffix = f"{int(time.time() * 1000)}{rng.randint(100000, 999999)}"
        orc_id = f"{product_name}_WF_{uuid.uuid4()}{suffix}"
        if orc_id not in used_set:
            used_set.add(orc_id)
            return orc_id
    raise RuntimeError("Could not generate unique orcJourneyID after 100 attempts")


def _unique_numeric_id(
    rng: random.Random,
    length: int,
    used: set[str],
) -> str:
    for _ in range(5000):
        val = _numeric_id(rng, length)
        if val not in used:
            used.add(val)
            return val
    raise RuntimeError(f"Could not generate unique {length}-digit ID after 5000 attempts")


def generate_journey_ids(
    rng: random.Random,
    *,
    used_partner: set[str] | None = None,
    used_bank: set[str] | None = None,
) -> dict[str, str]:
    partner_used = used_partner if used_partner is not None else set()
    bank_used = used_bank if used_bank is not None else set()
    return {
        "partnerJourneyID": _unique_numeric_id(rng, 12, partner_used),
        "bankJourneyID": _unique_numeric_id(rng, 11, bank_used),
    }


def generate_multibureau_ids(rng: random.Random) -> dict:
    app_id = _numeric_id(rng, 9)
    cust_id = _numeric_id(rng, 8)
    ack_id = _numeric_id(rng, 10)
    return {
        "applicationId": app_id,
        "custId": cust_id,
        "acknowledgementId": ack_id,
        "trackingIds": {
            "mbCibil": _numeric_id(rng, 10),
            "mbEquifax": _numeric_id(rng, 10),
            "mbHighMark": _numeric_id(rng, 10),
        },
        "eot": {
            "applicationId": _numeric_id(rng, 6),
            "custId": _numeric_id(rng, 6),
            "acknowledgementId": _numeric_id(rng, 10),
            "sentToCibil": "Y",
            "sentToEquifax": rng.choice(["Y", "N"]),
            "sentToExperian": rng.choice(["Y", "N"]),
            "sentToChm": rng.choice(["Y", "N"]),
        },
    }


def generate_perfios_ids(rng: random.Random, txn_suffix: str = "applicant") -> dict:
    return {
        "perfiosTransactionId": f"KKH{rng.randint(10**14, 10**15 - 1)}",
        "customerTransactionId": f"D{rng.randint(10, 99)}I{_numeric_id(rng, 6)}H0W1",
        "txnId": f"{uuid.uuid4()}{rng.randint(10**10, 10**11 - 1)}_{txn_suffix}",
    }


def generate_posidex_ids(rng: random.Random, *, template_rows: int = 12, match_count: int = 0) -> dict:
    extra_rows = max(template_rows - 1, match_count, 1)
    return {
        "soaAppId": _numeric_id(rng, 12),
        "soaMatchAppIds": [_numeric_id(rng, 7) for _ in range(extra_rows)],
    }


def generate_hunter_ids(rng: random.Random, scenario: str) -> dict:
    if scenario == "fraud-hit":
        return {"totalMatchScore": str(rng.randint(800, 1200)), "matches": "1"}
    if scenario == "clean-approval":
        return {"totalMatchScore": str(rng.randint(0, 100)), "matches": "0"}
    return {
        "totalMatchScore": str(rng.randint(0, 500)),
        "matches": str(rng.randint(0, 1)),
    }


def generate_system_ids(
    orc_journey_id: str,
    rng: random.Random,
    scenario: str = "clean-approval",
    *,
    scenario_config: dict | None = None,
) -> dict:
    posidex_cfg = (scenario_config or {}).get("posidex", {})
    match_count = int(posidex_cfg.get("matchCount", 0))
    from .spec_templates import posidex_template_row_count

    template_rows = posidex_template_row_count()
    return {
        "orcJourneyID": orc_journey_id,
        "multibureau": generate_multibureau_ids(rng),
        "perfios": generate_perfios_ids(rng),
        "posidex": generate_posidex_ids(rng, template_rows=template_rows, match_count=match_count),
        "hunter": generate_hunter_ids(rng, scenario),
    }

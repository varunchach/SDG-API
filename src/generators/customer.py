"""Synthetic customer + journey record generation."""

from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Any

from faker import Faker

from .indian_identity import (
    INDIAN_EMPLOYERS,
    INDIAN_FIRST_NAMES_FEMALE,
    INDIAN_FIRST_NAMES_MALE,
    pick_indian_name,
    pick_location,
    unique_customer_id,
    unique_email,
    unique_mobile,
    unique_pan,
)
from .scenarios import SCENARIO_NAMES, load_scenario
from .spec_builder import build_ack_response, build_initiate_request
from .system_ids import (
    generate_journey_ids,
    generate_orc_journey_id,
    generate_system_ids,
)
from .template_filler import fill_all_callbacks
from .uniqueness import IdentityRegistry
from .validate import validate_record

SCENARIOS = SCENARIO_NAMES


def _age_from_dob(dob: date) -> str:
    today = date.today()
    years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return str(max(21, min(years, 65)))


def _format_dob(dob: date) -> str:
    return dob.isoformat()


def _loan_amount(rng: random.Random) -> str:
    amount = rng.choice([500_000, 1_000_000, 1_500_000, 2_000_000, 2_500_000, 3_000_000])
    return str(amount)


def _infer_gender(first_name: str, rng: random.Random) -> str:
    if first_name in INDIAN_FIRST_NAMES_FEMALE:
        return "F"
    if first_name in INDIAN_FIRST_NAMES_MALE:
        return "M"
    return rng.choice(["M", "F"])


def _parse_dob(dob: str) -> date:
    try:
        parsed = date.fromisoformat(dob.strip())
    except ValueError as exc:
        raise ValueError("dob must be YYYY-MM-DD") from exc
    age = int(_age_from_dob(parsed))
    if age < 21 or age > 65:
        raise ValueError("dob must imply age between 21 and 65")
    return parsed


def _parse_applicant_name(full_name: str, last_name: str | None = None) -> tuple[str, str, str]:
    """Split full name into (fName, mName, lName) uppercase."""
    first = full_name.strip().upper()
    if not first:
        raise ValueError("name is required")

    if last_name and last_name.strip():
        parts = first.split()
        if len(parts) >= 2:
            return parts[0], " ".join(parts[1:]), last_name.strip().upper()
        return first, "", last_name.strip().upper()

    parts = first.split()
    if len(parts) == 1:
        raise ValueError("enter full name (first and last) or provide lName separately")
    if len(parts) == 2:
        return parts[0], "", parts[1]
    return parts[0], " ".join(parts[1:-1]), parts[-1]


def generate_customer_profile(
    rng: random.Random,
    faker: Faker,
    registry: IdentityRegistry,
    *,
    user_index: str = "0",
    user_type: str = "applicant",
    gender: str | None = None,
    record_seq: int | None = None,
) -> dict[str, Any]:
    """One canonical customer profile — source of truth for all producer systems."""
    gender = gender or rng.choice(["M", "F"])

    first, middle, last = pick_indian_name(rng, gender)
    pan = unique_pan(last, rng, registry.pans)
    registry.pans.add(pan)

    mobile = unique_mobile(rng, registry.mobiles)
    registry.mobiles.add(mobile)

    email = unique_email(first, last, rng, registry.emails, seq=record_seq)
    registry.emails.add(email)

    customer_id = unique_customer_id(rng, registry.customer_ids)
    registry.customer_ids.add(customer_id)

    age_years = rng.randint(25, 55)
    dob = date.today() - timedelta(days=age_years * 365 + rng.randint(0, 364))

    loc = pick_location(rng)
    street = faker.street_name().upper()
    area = faker.city_suffix().upper() if rng.random() < 0.5 else f"SECTOR {rng.randint(1, 20)}"

    return {
        "userIndex": user_index,
        "userType": user_type,
        "firstName": first,
        "middleName": middle,
        "lastName": last,
        "fullName": " ".join(p for p in (first, middle, last) if p),
        "pan": pan,
        "dob": _format_dob(dob),
        "gender": gender,
        "age": _age_from_dob(dob),
        "email": email,
        "mobile": mobile,
        "addressType": "CURRENT",
        "addressLine1": f"{street} {loc['city']} {loc['state']}",
        "addressLine2": area,
        "addressLine3": faker.building_number() if rng.random() < 0.6 else "",
        "addressLine4": loc["city"],
        "city": loc["city"],
        "state": loc["state"],
        "pinCode": loc["pinCode"],
        "employerName": rng.choice(INDIAN_EMPLOYERS),
        "loanAmount": _loan_amount(rng),
        "customerId": customer_id,
    }


def generate_customer_profile_from_identity(
    rng: random.Random,
    faker: Faker,
    registry: IdentityRegistry,
    *,
    full_name: str,
    dob: str,
    pan: str,
    last_name: str | None = None,
    user_index: str = "0",
    user_type: str = "applicant",
    record_seq: int | None = None,
) -> dict[str, Any]:
    """Build profile from user-supplied name/DOB/PAN; synthesize all other fields."""
    from .validate import PAN_RE

    first, middle, last = _parse_applicant_name(full_name, last_name)
    pan = pan.strip().upper()
    if not PAN_RE.match(pan):
        raise ValueError(f"invalid PAN format: {pan}")
    if pan in registry.pans:
        raise ValueError(f"PAN already used in this session: {pan}")
    registry.pans.add(pan)

    parsed_dob = _parse_dob(dob)
    gender = _infer_gender(first, rng)

    mobile = unique_mobile(rng, registry.mobiles)
    registry.mobiles.add(mobile)

    email = unique_email(first, last, rng, registry.emails, seq=record_seq)
    registry.emails.add(email)

    customer_id = unique_customer_id(rng, registry.customer_ids)
    registry.customer_ids.add(customer_id)

    loc = pick_location(rng)
    street = faker.street_name().upper()
    area = faker.city_suffix().upper() if rng.random() < 0.5 else f"SECTOR {rng.randint(1, 20)}"

    return {
        "userIndex": user_index,
        "userType": user_type,
        "firstName": first,
        "middleName": middle,
        "lastName": last,
        "fullName": " ".join(p for p in (first, middle, last) if p),
        "pan": pan,
        "dob": _format_dob(parsed_dob),
        "gender": gender,
        "age": _age_from_dob(parsed_dob),
        "email": email,
        "mobile": mobile,
        "addressType": "CURRENT",
        "addressLine1": f"{street} {loc['city']} {loc['state']}",
        "addressLine2": area,
        "addressLine3": faker.building_number() if rng.random() < 0.6 else "",
        "addressLine4": loc["city"],
        "city": loc["city"],
        "state": loc["state"],
        "pinCode": loc["pinCode"],
        "employerName": rng.choice(INDIAN_EMPLOYERS),
        "loanAmount": _loan_amount(rng),
        "customerId": customer_id,
    }


def generate_journey_context(
    rng: random.Random,
    profile: dict[str, Any],
    registry: IdentityRegistry,
    *,
    partner_id: str = "FYNDNA",
    channel_id: str = "CHANNEL_FYNDNA_HL1",
    product_name: str = "FYNDNA_HL1",
    scenario: str = "clean-approval",
) -> dict[str, Any]:
    journey_ids = generate_journey_ids(
        rng,
        used_partner=registry.partner_journey_ids,
        used_bank=registry.bank_journey_ids,
    )
    orc_id = generate_orc_journey_id(product_name, rng, used=registry.orc_journey_ids)
    perfios = generate_system_ids(orc_id, rng, scenario)["perfios"]

    return {
        **journey_ids,
        "orcJourneyID": orc_id,
        "partnerID": partner_id,
        "channelID": channel_id,
        "productName": product_name,
        "scenario": scenario,
        "productDetails": {
            "multibureau": {"loanType": "HOU", "responseFormat": "08"},
            "perfios": {
                "txnId": perfios["txnId"],
                "perfiosTransactionId": perfios["perfiosTransactionId"],
            },
            "posidex": {
                "sourceId": "",
                "productId": "",
                "priority": "",
                "matchingProfile": "",
                "branchId": "",
            },
            "hunter": {
                "hunterProductPart1": "HLS_I",
                "hunterProductPart2": rng.choice(["MUM", "DEL", "BLR", "CHN"]),
            },
        },
        "status": "GENERATED",
    }


def generate_customer_record(
    rng: random.Random,
    faker: Faker,
    registry: IdentityRegistry,
    *,
    record_id: int,
    scenario: str | None = None,
) -> dict[str, Any]:
    """
    Full synthetic record: profile + journey + spec initiate/ACK + callbacks.
    Profile identity is consistent across all producer payloads.
    """
    scenario_name = scenario or rng.choice(SCENARIOS)
    scenario_config = load_scenario(scenario_name)

    profile = generate_customer_profile(
        rng, faker, registry, user_index="0", user_type="applicant", record_seq=record_id
    )
    co_profile = generate_customer_profile(
        rng, faker, registry, user_index="1", user_type="coapplicant", record_seq=record_id + 10000
    )
    journey = generate_journey_context(rng, profile, registry, scenario=scenario_name)
    system_ids = generate_system_ids(
        journey["orcJourneyID"], rng, scenario_name, scenario_config=scenario_config
    )

    initiate_request = build_initiate_request(profile, journey, co_profile=co_profile)
    ack_response = build_ack_response(journey)
    callbacks = fill_all_callbacks(
        profile, journey, system_ids, scenario_config, co_applicant_count=1
    )

    record = {
        "recordId": f"CUST-{record_id:04d}",
        "scenario": scenario_name,
        "profile": profile,
        "journey": journey,
        "systemIds": system_ids,
        "initiateRequest": initiate_request,
        "ackResponse": ack_response,
        "callbacks": callbacks,
    }

    errors = validate_record(record)
    if errors:
        raise ValueError(f"Validation failed for {record['recordId']}: {errors[:3]}")
    return record


def generate_customer_batch(
    count: int,
    *,
    seed: int = 42,
) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    faker = Faker("en_IN")
    faker.seed_instance(seed)

    registry = IdentityRegistry()
    records = []
    for i in range(1, count + 1):
        records.append(
            generate_customer_record(rng, faker, registry, record_id=i)
        )

    dup_errors = registry.audit_records(records)
    if dup_errors:
        raise ValueError(f"Batch uniqueness check failed: {dup_errors}")

    return records

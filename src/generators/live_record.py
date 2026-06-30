"""On-the-fly initiateRequest generation — same spec format as demo/batch."""

from __future__ import annotations

import random
from datetime import datetime
from typing import Any

from faker import Faker

from .customer import (
    generate_customer_profile,
    generate_customer_profile_from_identity,
    generate_journey_context,
)
from .scenarios import SCENARIO_NAMES
from .spec_builder import build_initiate_request
from .uniqueness import IdentityRegistry


def _fresh_rng() -> tuple[random.Random, Faker]:
    seed = int(datetime.utcnow().timestamp() * 1000) % (2**31)
    rng = random.Random(seed)
    faker = Faker("en_IN")
    faker.seed_instance(seed)
    return rng, faker


def _generate_one(
    rng: random.Random,
    faker: Faker,
    registry: IdentityRegistry,
    scenario_name: str,
) -> dict[str, Any]:
    profile = generate_customer_profile(
        rng,
        faker,
        registry,
        user_index="0",
        user_type="applicant",
        record_seq=int(rng.randint(1, 99999)),
    )
    co_profile = generate_customer_profile(
        rng,
        faker,
        registry,
        user_index="1",
        user_type="coapplicant",
        record_seq=int(rng.randint(1, 99999)),
    )
    journey = generate_journey_context(rng, profile, registry, scenario=scenario_name)
    initiate_request = build_initiate_request(profile, journey, co_profile=co_profile)
    return {
        "initiateRequest": initiate_request,
        "scenario": scenario_name,
    }


def generate_initiate_from_identity(
    *,
    full_name: str,
    dob: str,
    pan_no: str,
    last_name: str | None = None,
    scenario: str | None = None,
) -> dict[str, Any]:
    """
    Build full EE spec initiateRequest from minimal identity input.
    User supplies name + DOB + PAN; all other fields are synthesized.
    """
    rng, faker = _fresh_rng()
    registry = IdentityRegistry()
    scenario_name = scenario if scenario in SCENARIO_NAMES else rng.choice(SCENARIO_NAMES)

    profile = generate_customer_profile_from_identity(
        rng,
        faker,
        registry,
        full_name=full_name,
        dob=dob,
        pan=pan_no,
        last_name=last_name,
        user_index="0",
        user_type="applicant",
        record_seq=int(rng.randint(1, 99999)),
    )
    co_profile = generate_customer_profile(
        rng,
        faker,
        registry,
        user_index="1",
        user_type="coapplicant",
        record_seq=int(rng.randint(1, 99999)),
    )
    journey = generate_journey_context(rng, profile, registry, scenario=scenario_name)
    initiate_request = build_initiate_request(profile, journey, co_profile=co_profile)

    demog = initiate_request["applicant"]["customerDemog"]
    addr = demog["address"][0]
    co = initiate_request["coApplicants"]["coApplicantArray"][0]["customerDemog"]

    return {
        "initiateRequest": initiate_request,
        "scenario": scenario_name,
        "generatedDetails": {
            "applicant": {
                "name": demog["name"][0],
                "dob": demog["dob"],
                "age": demog["age"],
                "gender": demog["gender"],
                "panNo": demog["ids"]["panNo"],
                "emailId1": demog["emailId1"],
                "mobile": demog.get("mobile", ""),
                "address": addr,
                "employerName": initiate_request["applicant"]["employmentDetails"]["employerName"],
                "customerId": initiate_request["applicant"]["bankingDetails"]["accountInfo"][0]["customerId"],
                "loanAmount": initiate_request["applicant"]["bankingDetails"]["loanDetails"]["loanAmount"],
            },
            "coApplicant": {
                "name": co["name"][0],
                "panNo": co["ids"]["panNo"],
                "address": co["address"][0],
            },
            "journey": {
                "partnerJourneyID": initiate_request["contextParameter"]["partnerJourneyID"],
                "bankJourneyID": initiate_request["contextParameter"]["bankJourneyID"],
            },
        },
    }


def generate_random_initiate_request(
    scenario: str | None = None,
) -> dict[str, Any]:
    """
    Build a full EE spec initiateRequest on the fly (no orcJourneyID).
    Same structure as batch-generated records / demo UI.
    """
    rng, faker = _fresh_rng()
    registry = IdentityRegistry()
    scenario_name = scenario if scenario in SCENARIO_NAMES else rng.choice(SCENARIO_NAMES)
    return _generate_one(rng, faker, registry, scenario_name)

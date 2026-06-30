"""Run mock producer callbacks synchronously from an EE initiateRequest."""

from __future__ import annotations

import random
import uuid
from typing import Any

from src.api.initiate_parser import (
    callback_order_for_initiate,
    co_applicant_count,
    journey_from_initiate,
    profile_from_initiate,
)
from src.generators.scenarios import load_scenario
from src.generators.spec_builder import build_ack_response
from src.generators.system_ids import generate_orc_journey_id, generate_system_ids
from src.generators.template_filler import (
    fill_hunter,
    fill_mb_cibil,
    fill_mb_equifax,
    fill_mb_highmark,
    fill_mb_mbeot,
    fill_perfios,
    fill_posidex,
    fill_summary,
)
from src.generators.validate import validate_record

PRODUCER_REPORT_TYPES = frozenset({
    "mbCibil",
    "mbEquifax",
    "mbHighMark",
    "mbMbEot",
    "perfios",
    "posidex",
    "hunter",
    "summary",
})


def _assert_initiate_valid(initiate_request: dict[str, Any]) -> None:
    if "orcJourneyID" in initiate_request.get("contextParameter", {}):
        raise ValueError("initiateRequest must not contain orcJourneyID")


def _prepare_journey(
    initiate_request: dict[str, Any],
    scenario_name: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], int]:
    _assert_initiate_valid(initiate_request)
    rng = random.Random()
    ctx = initiate_request["contextParameter"]
    orc_id = generate_orc_journey_id(ctx["productName"], rng)
    profile = profile_from_initiate(initiate_request)
    journey = journey_from_initiate(initiate_request, orc_id)
    scenario = load_scenario(scenario_name)
    system_ids = generate_system_ids(orc_id, rng, scenario_name, scenario_config=scenario)
    ack = build_ack_response(journey)
    co_count = co_applicant_count(initiate_request)
    return profile, journey, system_ids, scenario, ack, co_count


def fill_producer_callback(
    report_type: str,
    profile: dict[str, Any],
    journey: dict[str, Any],
    system_ids: dict[str, Any],
    scenario: dict[str, Any],
    *,
    partial_callbacks: dict[str, Any] | None = None,
    co_count: int = 0,
) -> dict[str, Any]:
    partial = partial_callbacks or {}
    if report_type == "mbCibil":
        return fill_mb_cibil(profile, journey, system_ids, scenario)
    if report_type == "mbEquifax":
        return fill_mb_equifax(profile, journey, system_ids, scenario)
    if report_type == "mbHighMark":
        return fill_mb_highmark(profile, journey, system_ids, scenario)
    if report_type == "mbMbEot":
        return fill_mb_mbeot(journey, system_ids)
    if report_type == "perfios":
        return fill_perfios(profile, journey, system_ids, scenario)
    if report_type == "posidex":
        return fill_posidex(profile, journey, system_ids, scenario)
    if report_type == "hunter":
        return fill_hunter(journey, system_ids, scenario)
    if report_type == "summary":
        return fill_summary(journey, partial, scenario, co_applicant_count=co_count)
    raise ValueError(f"Unknown reportType: {report_type}")


def run_sync_producers(
    initiate_request: dict[str, Any],
    scenario_name: str,
    *,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Synchronous full mock journey: ACK + all producer callbacks implied by productDetails.
    """
    profile, journey, system_ids, scenario, ack, co_count = _prepare_journey(
        initiate_request, scenario_name
    )
    callback_order = callback_order_for_initiate(initiate_request)
    callbacks: dict[str, Any] = {}
    for report_type in callback_order:
        callbacks[report_type] = fill_producer_callback(
            report_type,
            profile,
            journey,
            system_ids,
            scenario,
            partial_callbacks=callbacks,
            co_count=co_count,
        )

    result = {
        "recordId": f"SYNC-{uuid.uuid4().hex[:12].upper()}",
        "scenario": scenario_name,
        "orcJourneyID": journey["orcJourneyID"],
        "initiateRequest": initiate_request,
        "ackResponse": ack,
        "callbacks": callbacks,
        "callbackOrder": callback_order,
        "profile": profile,
        "journey": journey,
        "systemIds": system_ids,
    }
    if validate:
        record = {
            "scenario": scenario_name,
            "profile": profile,
            "journey": journey,
            "initiateRequest": initiate_request,
            "ackResponse": ack,
            "callbacks": callbacks,
        }
        errors = validate_record(record)
        if errors:
            result["validationErrors"] = errors
    return result


def run_sync_single_producer(
    initiate_request: dict[str, Any],
    scenario_name: str,
    report_type: str,
    *,
    validate: bool = False,
) -> dict[str, Any]:
    """Generate one producer callback from an EE initiateRequest."""
    if report_type not in PRODUCER_REPORT_TYPES:
        raise ValueError(f"Unknown reportType. Choose from {sorted(PRODUCER_REPORT_TYPES)}")

    profile, journey, system_ids, scenario, ack, co_count = _prepare_journey(
        initiate_request, scenario_name
    )

    partial: dict[str, Any] = {}
    if report_type == "summary":
        for rt in callback_order_for_initiate(initiate_request):
            if rt == "summary":
                break
            partial[rt] = fill_producer_callback(
                rt, profile, journey, system_ids, scenario, co_count=co_count
            )

    payload = fill_producer_callback(
        report_type,
        profile,
        journey,
        system_ids,
        scenario,
        partial_callbacks=partial,
        co_count=co_count,
    )

    result = {
        "recordId": f"SYNC-{uuid.uuid4().hex[:12].upper()}",
        "scenario": scenario_name,
        "reportType": report_type,
        "orcJourneyID": journey["orcJourneyID"],
        "ackResponse": ack,
        "callback": payload,
        "profile": profile,
        "journey": journey,
        "systemIds": system_ids,
    }
    return result

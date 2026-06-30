"""Async callbacks for live journeys + CSV export on completion."""

from __future__ import annotations

import asyncio
import os
import random
import uuid
from typing import Any

from src.api.initiate_parser import (
    callback_order_for_initiate,
    co_applicant_count,
    journey_from_initiate,
    profile_from_initiate,
)
from src.api_live.csv_export import append_journey_to_csv
from src.api_live.storage import LiveJourneyRecord, live_store
from src.producer.sync_service import fill_producer_callback
from src.generators.scenarios import load_scenario
from src.generators.spec_builder import build_ack_response
from src.generators.system_ids import generate_orc_journey_id, generate_system_ids

CALLBACK_DELAY_SECONDS = float(os.environ.get("CALLBACK_DELAY_SECONDS", "3"))


def _on_journey_complete(rec: LiveJourneyRecord) -> None:
    try:
        result = append_journey_to_csv(rec)
        rec.csv_saved = True
        rec.csv_location = result["location"]
    except Exception as exc:
        rec.csv_location = f"ERROR: {exc}"


live_store.set_on_complete(_on_journey_complete)


def _fill_callback(
    report_type: str,
    profile: dict[str, Any],
    journey: dict[str, Any],
    system_ids: dict[str, Any],
    scenario: dict[str, Any],
    partial_callbacks: dict[str, Any],
    co_count: int,
) -> dict[str, Any]:
    return fill_producer_callback(
        report_type,
        profile,
        journey,
        system_ids,
        scenario,
        partial_callbacks=partial_callbacks,
        co_count=co_count,
    )


async def dispatch_live_callbacks(
    orc_journey_id: str,
    profile: dict[str, Any],
    journey: dict[str, Any],
    system_ids: dict[str, Any],
    scenario_name: str,
    callback_order: list[str],
    co_count: int,
) -> None:
    scenario = load_scenario(scenario_name)
    partial: dict[str, Any] = {}
    for report_type in callback_order:
        await asyncio.sleep(CALLBACK_DELAY_SECONDS)
        payload = _fill_callback(
            report_type, profile, journey, system_ids, scenario, partial, co_count
        )
        partial[report_type] = payload
        live_store.add_callback(orc_journey_id, report_type, payload)


def start_live_journey_from_initiate(
    initiate_request: dict[str, Any],
    scenario: str,
) -> tuple[LiveJourneyRecord, dict[str, Any], dict[str, Any], dict[str, Any], int]:
    """
    Same initiate → ACK → callbacks pipeline as demo API.
    initiateRequest must be full EE spec JSON (no orcJourneyID).
    """
    if "orcJourneyID" in initiate_request.get("contextParameter", {}):
        raise ValueError("initiateRequest must not contain orcJourneyID")

    ctx = initiate_request["contextParameter"]
    rng = random.Random()
    orc_id = generate_orc_journey_id(ctx["productName"], rng)
    journey = journey_from_initiate(initiate_request, orc_id)
    profile = profile_from_initiate(initiate_request)
    scenario_config = load_scenario(scenario)
    system_ids = generate_system_ids(orc_id, rng, scenario, scenario_config=scenario_config)
    ack = build_ack_response(journey)
    callback_order = callback_order_for_initiate(initiate_request)
    co_count = co_applicant_count(initiate_request)

    record = LiveJourneyRecord(
        record_id=f"LIVE-{uuid.uuid4().hex[:12].upper()}",
        orc_journey_id=orc_id,
        partner_journey_id=ctx["partnerJourneyID"],
        bank_journey_id=ctx["bankJourneyID"],
        scenario=scenario,
        profile=profile,
        initiate_request=initiate_request,
        ack_response=ack,
        callback_order=callback_order,
    )
    live_store.save(record)
    return record, profile, journey, system_ids, co_count

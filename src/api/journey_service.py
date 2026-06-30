"""Initiate journey → ACK → async producer callbacks."""

from __future__ import annotations

import asyncio
import os
import random
from typing import Any

from src.api.initiate_parser import (
    callback_order_for_initiate,
    co_applicant_count,
    journey_from_initiate,
    profile_from_initiate,
)
from src.api.storage import JourneyRecord, store
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

CALLBACK_DELAY_SECONDS = float(os.environ.get("CALLBACK_DELAY_SECONDS", "3"))


def _fill_callback(
    report_type: str,
    profile: dict[str, Any],
    journey: dict[str, Any],
    system_ids: dict[str, Any],
    scenario: dict[str, Any],
    partial_callbacks: dict[str, Any],
    co_count: int,
) -> dict[str, Any]:
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
        return fill_summary(journey, partial_callbacks, scenario, co_applicant_count=co_count)
    raise ValueError(f"Unknown reportType: {report_type}")


async def _dispatch_callbacks(
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
    delay = CALLBACK_DELAY_SECONDS

    for report_type in callback_order:
        await asyncio.sleep(delay)
        payload = _fill_callback(
            report_type, profile, journey, system_ids, scenario, partial, co_count
        )
        partial[report_type] = payload
        store.add_callback(orc_journey_id, report_type, payload)



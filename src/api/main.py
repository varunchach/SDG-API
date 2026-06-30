"""FastAPI mock Eligibility Engine — Initiate → ACK → async callbacks."""

from __future__ import annotations

import asyncio
import random
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.api.initiate_parser import (
    callback_order_for_initiate,
    co_applicant_count,
    journey_from_initiate,
    profile_from_initiate,
)
from src.api.journey_service import CALLBACK_DELAY_SECONDS, _dispatch_callbacks
from src.api.records_loader import list_records, load_record
from src.api.storage import JourneyRecord, store
from src.generators.scenarios import SCENARIO_NAMES, load_scenario
from src.generators.spec_builder import build_ack_response
from src.generators.system_ids import generate_orc_journey_id, generate_system_ids

ROOT = Path(__file__).resolve().parents[2]
UI_DIR = ROOT / "ui"

app = FastAPI(
    title="HDFC Eligibility Engine — Mock Producer",
    description="Partner Initiate → sync ACK → async producer callbacks → Summary",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class InitiateBody(BaseModel):
    initiateRequest: dict[str, Any]
    scenario: str = Field(default="clean-approval")


def _prepare_journey(
    initiate_request: dict[str, Any],
    scenario: str,
) -> tuple[JourneyRecord, dict[str, Any], dict[str, Any], dict[str, Any], int]:
    if "orcJourneyID" in initiate_request.get("contextParameter", {}):
        raise HTTPException(400, "initiateRequest must not contain orcJourneyID")

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

    record = JourneyRecord(
        orc_journey_id=orc_id,
        partner_journey_id=ctx["partnerJourneyID"],
        bank_journey_id=ctx["bankJourneyID"],
        scenario=scenario,
        initiate_request=initiate_request,
        ack_response=ack,
        callback_order=callback_order,
        status="INITIATED",
    )
    store.save(record)
    return record, profile, journey, system_ids, co_count


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "callbackDelaySeconds": str(CALLBACK_DELAY_SECONDS)}


@app.get("/api/scenarios")
def scenarios() -> dict[str, Any]:
    return {"scenarios": list(SCENARIO_NAMES)}


@app.get("/api/records")
def get_records() -> dict[str, Any]:
    return {"records": list_records()}


@app.get("/api/records/{record_id}")
def get_record(record_id: str) -> dict[str, Any]:
    rec = load_record(record_id)
    if not rec:
        raise HTTPException(404, f"Record {record_id} not found. Run generate_customers.py first.")
    return rec


@app.get("/api/journeys")
def list_journeys() -> dict[str, Any]:
    return {"journeys": store.list_all()}


@app.get("/api/journey/{orc_journey_id}")
def get_journey(orc_journey_id: str) -> dict[str, Any]:
    rec = store.get(orc_journey_id)
    if not rec:
        raise HTTPException(404, "Journey not found")
    return rec.to_status_dict()


@app.get("/api/journey/{orc_journey_id}/callback/{report_type}")
def get_callback(orc_journey_id: str, report_type: str) -> dict[str, Any]:
    rec = store.get(orc_journey_id)
    if not rec:
        raise HTTPException(404, "Journey not found")
    if report_type not in rec.callbacks:
        raise HTTPException(404, f"Callback {report_type} not yet received")
    return rec.callbacks[report_type]


@app.post("/api/journey/initiate")
async def initiate_journey(body: InitiateBody) -> dict[str, Any]:
    if body.scenario not in SCENARIO_NAMES:
        raise HTTPException(400, f"Unknown scenario. Choose from {SCENARIO_NAMES}")

    record, profile, journey, system_ids, co_count = _prepare_journey(
        body.initiateRequest, body.scenario
    )

    asyncio.create_task(
        _dispatch_callbacks(
            record.orc_journey_id,
            profile,
            journey,
            system_ids,
            body.scenario,
            record.callback_order,
            co_count,
        )
    )

    return {
        "orcJourneyID": record.orc_journey_id,
        "scenario": body.scenario,
        "callbackOrder": record.callback_order,
        "callbackDelaySeconds": CALLBACK_DELAY_SECONDS,
        "ackResponse": record.ack_response,
    }


@app.post("/api/journey/initiate/from-record/{record_id}")
async def initiate_from_record(record_id: str, scenario: str | None = None) -> dict[str, Any]:
    rec = load_record(record_id)
    if not rec:
        raise HTTPException(404, f"Record {record_id} not found")
    scen = scenario or rec.get("scenario", "clean-approval")
    body = InitiateBody(initiateRequest=rec["initiateRequest"], scenario=scen)
    return await initiate_journey(body)


@app.get("/")
def ui_index() -> FileResponse:
    return FileResponse(UI_DIR / "index.html")


if UI_DIR.exists():
    app.mount("/ui", StaticFiles(directory=UI_DIR), name="ui")

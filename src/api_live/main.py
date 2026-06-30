"""Live API — same initiateRequest spec as demo; generated on the fly + CSV export."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.api_live.csv_export import local_csv_path, storage_info
from src.api_live.journey_service import (
    CALLBACK_DELAY_SECONDS,
    dispatch_live_callbacks,
    start_live_journey_from_initiate,
)
from src.api_live.storage import live_store
from src.generators.live_record import (
    generate_initiate_from_identity,
    generate_random_initiate_request,
)
from src.generators.scenarios import SCENARIO_NAMES
from src.producer.producer_highlights import (
    PRODUCER_TITLES,
    extract_all_producer_highlights,
    extract_producer_highlights,
)
from src.generators.spec_templates import load_spec_initiate_request
from src.producer.sync_service import (
    PRODUCER_REPORT_TYPES,
    run_sync_producers,
    run_sync_single_producer,
)

ROOT = Path(__file__).resolve().parents[2]
UI_DIR = ROOT / "ui_live"

app = FastAPI(
    title="HDFC Eligibility Engine — Live Generator",
    description="On-the-fly initiateRequest → ACK → callbacks → CSV export",
    version="1.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class InitiateBody(BaseModel):
    """POC wrapper — partners send raw EE JSON; this wrapper is optional."""
    initiateRequest: dict[str, Any] = Field(
        description=(
            "EE initiate payload per EE- initiate request V1.0.txt: contextParameter, "
            "applicant (with productDetails inside), coApplicants, sourceApp."
        )
    )
    scenario: str = Field(default="clean-approval")


class BuildInitiateBody(BaseModel):
    """Minimal identity → full EE initiateRequest."""
    name: str = Field(description="Applicant full name, e.g. PRANAV SANTOSH")
    dob: str = Field(description="Date of birth YYYY-MM-DD")
    panNo: str = Field(description="PAN number AAAAA9999A")
    lName: str | None = Field(default=None, description="Optional last name if name is first name only")
    scenario: str = Field(default="clean-approval")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "mode": "live",
        "callbackDelaySeconds": CALLBACK_DELAY_SECONDS,
        "csvStorage": storage_info(),
    }


@app.get("/api/scenarios")
def scenarios() -> dict[str, Any]:
    return {"scenarios": list(SCENARIO_NAMES)}


@app.get("/api/samples/ee-initiate-request")
def sample_ee_initiate_request() -> dict[str, Any]:
    """Exact partner input from EligibilityEngine_SpecDoc_SampleFiles/EE- initiate request V1.0.txt."""
    return load_spec_initiate_request()


def _parse_initiate_payload(
    body: dict[str, Any],
    scenario_query: str,
) -> tuple[dict[str, Any], str]:
    """
    Accept either:
    - Raw EE initiate JSON (contextParameter + applicant at root), or
    - POC wrapper { initiateRequest, scenario }.
    """
    if "initiateRequest" in body:
        initiate = body["initiateRequest"]
        scenario = body.get("scenario", scenario_query)
    elif "contextParameter" in body and "applicant" in body:
        initiate = body
        scenario = scenario_query
    else:
        raise HTTPException(
            400,
            "Expected EE initiate JSON (contextParameter, applicant, coApplicants, sourceApp) "
            "or wrapper { initiateRequest, scenario }. "
            "See GET /api/samples/ee-initiate-request.",
        )
    if not isinstance(initiate, dict):
        raise HTTPException(400, "initiateRequest must be a JSON object")
    return initiate, scenario


def _run_eligibility_callbacks(initiate_request: dict[str, Any], scenario: str) -> dict[str, Any]:
    if scenario not in SCENARIO_NAMES:
        raise HTTPException(400, f"Unknown scenario. Choose from {SCENARIO_NAMES}")
    try:
        result = run_sync_producers(initiate_request, scenario, validate=True)
        if result.get("callbacks"):
            result["producerHighlights"] = extract_all_producer_highlights(
                initiate_request, result["callbacks"]
            )
        return result
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/eligibility/generate-callbacks")
def generate_callbacks(
    body: dict[str, Any] = Body(
        ...,
        examples={
            "ee_spec_initiate": {
                "summary": "Partner initiate (EE- initiate request V1.0.txt)",
                "value": {
                    "contextParameter": {
                        "partnerJourneyID": "345005711293",
                        "bankJourneyID": "45562927123",
                        "partnerID": "FYNDNA",
                        "channelID": "CHANNEL_FYNDNA_HL1",
                        "productName": "FYNDNA_HL1",
                    },
                    "applicant": {
                        "customerSegment": "INDIVIDUAL",
                        "productDetails": {
                            "multibureau": {"loanType": "HOU", "responseFormat": "08"},
                            "perfios": {},
                            "posidex": {},
                            "hunter": {},
                        },
                    },
                    "coApplicants": {"totalCoApplicants": "0", "coApplicantArray": []},
                    "sourceApp": {"constitution": ""},
                },
            },
            "poc_wrapper": {
                "summary": "Optional POC wrapper with scenario",
                "value": {"scenario": "clean-approval", "initiateRequest": {"contextParameter": {}}},
            },
        },
    ),
    scenario: str = Query(
        default="clean-approval",
        description="Callback outcome scenario (used when body is raw EE initiate JSON)",
    ),
) -> dict[str, Any]:
    """
    Primary API: POST the **exact EE initiate JSON** from the spec file.

    Body = contents of `EE- initiate request V1.0.txt` (no wrapper required).
    `productDetails` lives under `applicant`, not at root.
    Optional `?scenario=clean-approval` for mock callback outcomes.
    """
    initiate_request, scen = _parse_initiate_payload(body, scenario)
    return _run_eligibility_callbacks(initiate_request, scen)


@app.post("/api/initiate-request/build")
def build_initiate_request(body: BuildInitiateBody) -> dict[str, Any]:
    """Build full spec initiateRequest from name + DOB + PAN; synthesize everything else."""
    if body.scenario not in SCENARIO_NAMES:
        raise HTTPException(400, f"Unknown scenario. Choose from {SCENARIO_NAMES}")
    try:
        return generate_initiate_from_identity(
            full_name=body.name,
            dob=body.dob,
            pan_no=body.panNo,
            last_name=body.lName,
            scenario=body.scenario,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/initiate-request/random")
def random_initiate_request(scenario: str | None = None) -> dict[str, Any]:
    """Generate fully random spec initiateRequest (optional helper)."""
    if scenario and scenario not in SCENARIO_NAMES:
        raise HTTPException(400, f"Unknown scenario. Choose from {SCENARIO_NAMES}")
    return generate_random_initiate_request(scenario)


@app.get("/api/storage")
def get_storage_info() -> dict[str, Any]:
    return storage_info()


@app.get("/api/export/csv")
def download_csv() -> FileResponse:
    """Download accumulated eligibility results CSV."""
    info = storage_info()
    if info["backend"] == "s3":
        raise HTTPException(
            501,
            "CSV is stored in S3/MinIO — use bucket console or configure S3 download separately.",
        )
    path = local_csv_path()
    if not path or not Path(path).is_file():
        raise HTTPException(404, "No CSV file yet — complete a journey first.")
    return FileResponse(
        path,
        media_type="text/csv",
        filename="eligibility-records.csv",
    )


@app.get("/api/journey/{orc_journey_id}/export")
def download_journey(orc_journey_id: str) -> dict[str, Any]:
    """Full journey payload for JSON download (initiate + ACK + callbacks)."""
    rec = live_store.get(orc_journey_id)
    if not rec:
        raise HTTPException(404, "Journey not found")
    return {
        "recordId": rec.record_id,
        "scenario": rec.scenario,
        "orcJourneyID": rec.orc_journey_id,
        "status": rec.status,
        "initiateRequest": rec.initiate_request,
        "ackResponse": rec.ack_response,
        "callbacks": rec.callbacks,
        "callbackOrder": rec.callback_order,
        "callbacksReceived": list(rec.callbacks.keys()),
    }


@app.get("/api/journey/{orc_journey_id}")
def get_journey(orc_journey_id: str) -> dict[str, Any]:
    rec = live_store.get(orc_journey_id)
    if not rec:
        raise HTTPException(404, "Journey not found")
    status = rec.to_status_dict()
    if rec.callbacks:
        status["producerHighlights"] = extract_all_producer_highlights(
            rec.initiate_request, rec.callbacks
        )
    return status


@app.post("/api/producer/run")
def producer_run_all(
    body: dict[str, Any] = Body(...),
    scenario: str = Query(default="clean-approval"),
) -> dict[str, Any]:
    """Alias for POST /api/eligibility/generate-callbacks."""
    initiate_request, scen = _parse_initiate_payload(body, scenario)
    return _run_eligibility_callbacks(initiate_request, scen)


@app.post("/api/producer/{report_type}")
def producer_run_one(report_type: str, body: InitiateBody) -> dict[str, Any]:
    """Synchronous single producer: EE initiateRequest → one callback payload."""
    if body.scenario not in SCENARIO_NAMES:
        raise HTTPException(400, f"Unknown scenario. Choose from {SCENARIO_NAMES}")
    if report_type not in PRODUCER_REPORT_TYPES:
        raise HTTPException(400, f"Unknown reportType. Choose from {sorted(PRODUCER_REPORT_TYPES)}")
    try:
        result = run_sync_single_producer(
            body.initiateRequest, body.scenario, report_type
        )
        result["producerHighlights"] = {
            report_type: extract_producer_highlights(
                body.initiateRequest, report_type, result["callback"]
            )
        }
        return result
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/journey/initiate")
async def initiate_journey(body: InitiateBody) -> dict[str, Any]:
    """Same payload as demo: { initiateRequest, scenario }."""
    if body.scenario not in SCENARIO_NAMES:
        raise HTTPException(400, f"Unknown scenario. Choose from {SCENARIO_NAMES}")

    try:
        record, profile, journey, system_ids, co_count = start_live_journey_from_initiate(
            body.initiateRequest, body.scenario
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    asyncio.create_task(
        dispatch_live_callbacks(
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
        "recordId": record.record_id,
        "orcJourneyID": record.orc_journey_id,
        "scenario": body.scenario,
        "callbackOrder": record.callback_order,
        "callbackDelaySeconds": CALLBACK_DELAY_SECONDS,
        "ackResponse": record.ack_response,
        "initiateRequest": record.initiate_request,
        "csvStorage": storage_info(),
    }


@app.get("/")
def ui_index() -> FileResponse:
    return FileResponse(UI_DIR / "index.html")


if UI_DIR.exists():
    app.mount("/ui", StaticFiles(directory=UI_DIR), name="ui")

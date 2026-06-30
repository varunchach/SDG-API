# SDG-API — HDFC Eligibility Engine Mock Producer

Synthetic data generator and **mock Producer API** for HDFC Eligibility Engine loan-journey testing. Accepts EE-spec **Initiate Journey** JSON, returns synchronous **ACK**, and generates **producer callbacks** (CIBIL, Equifax, High Mark, Perfios, Posidex, Hunter, Summary).

All data is **synthetic** — no real bureau, Perfios, Posidex, or Hunter integration.

**Live POC (public):** https://hdfc-eligibility-live-default.apps.ocp.kxxfq.sandbox565.opentlc.com

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Local Setup](#local-setup)
- [Run Locally](#run-locally)
- [API Reference](#api-reference)
- [Sample curl Commands](#sample-curl-commands)
- [Scenarios](#scenarios)
- [Generate Batch Data](#generate-batch-data)
- [Validation & Smoke Tests](#validation--smoke-tests)
- [Deploy to OpenShift](#deploy-to-openshift)
- [Spec References](#spec-references)
- [Related Documentation](#related-documentation)

---

## Overview

### What this simulates

| Actor | Role |
|-------|------|
| **Partner** | Sends Initiate Journey request (EE spec JSON) |
| **Producer (this API)** | Returns ACK + mock async/sync callbacks per downstream system |

### Producer systems supported

| reportType | System |
|------------|--------|
| `mbCibil` | CIBIL (Multibureau) |
| `mbEquifax` | Equifax |
| `mbHighMark` | CRIF High Mark |
| `mbMbEot` | Multibureau End-of-Txn |
| `perfios` | Perfios (bank statement / income) |
| `posidex` | Posidex (dedupe / match) |
| `hunter` | Hunter (fraud) |
| `summary` | Eligibility summary |

### Two applications

| App | Entry point | Purpose |
|-----|-------------|---------|
| **Demo** | `src/api/main.py` | Preloaded customer records, demo UI |
| **Live** | `src/api_live/main.py` | On-the-fly generation, sync APIs, CSV export, customer-facing POC |

---

## Architecture

```
Partner / UI
    │
    ▼
FastAPI (Demo or Live)
    │
    ├── initiate_parser  →  profile + journey (canonical identity)
    ├── spec_builder     →  initiateRequest + ackResponse
    ├── template_filler  →  producer callbacks from spec .txt templates
    ├── scenarios        →  pass/fail / score overrides
    └── sync_service     →  instant ACK + all callbacks (Live)
    │
    ▼
Mock callbacks (mbCibil, perfios, posidex, hunter, summary, …)
```

**Design principles**

- **Spec fidelity** — JSON keys match `EligibilityEngine_SpecDoc_SampleFiles/` exactly
- **Single profile** — PAN, name, DOB consistent across initiate and every callback
- **Scenario-driven** — `data/scenarios/*.json` controls bureau scores, Hunter hits, summary outcomes
- **No orcJourneyID in initiate** — generated at submit time, echoed in ACK and callbacks

Detailed diagrams: [`docs/EligibilityEngine_Approach_and_Architecture.md`](docs/EligibilityEngine_Approach_and_Architecture.md)

---

## Project Structure

```
SDG-API/
├── src/
│   ├── api/              # Demo FastAPI + journey store
│   ├── api_live/         # Live FastAPI + CSV export
│   ├── generators/       # Faker, templates, spec builder, fillers
│   └── producer/         # Sync producer service + highlights
├── data/
│   ├── scenarios/        # Test behaviour configs
│   ├── samples/          # EE initiate JSON samples
│   └── templates/        # initiate-request, ack, callback JSON templates
├── EligibilityEngine_SpecDoc_SampleFiles/   # Authoritative EE spec samples (.txt)
├── ui/                   # Demo web UI
├── ui_live/              # Live web UI
├── openshift/            # OpenShift manifests (demo + live)
├── scripts/              # Generators, audits, smoke tests
├── docs/                 # Architecture + customer snapshot PDF
├── Dockerfile            # Demo image
├── Dockerfile.live       # Live image
├── requirements.txt      # Demo deps
└── requirements-live.txt # Live deps (+ boto3 for S3 CSV)
```

---

## Prerequisites

- **Python 3.11+**
- **pip** / **venv**
- **curl** (for API testing)
- **OpenShift CLI (`oc`)** — only for cluster deploy
- **jq** — optional, for pretty JSON output

---

## Local Setup

```bash
# Clone
git clone https://github.com/varunchach/SDG-API.git
cd SDG-API

# Virtual environment
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements-live.txt   # Live API (recommended)
# or
pip install -r requirements.txt        # Demo API only
```

---

## Run Locally

### Live API (recommended — sync producer + customer endpoints)

```bash
source .venv/bin/activate
uvicorn src.api_live.main:app --host 0.0.0.0 --port 8081
```

| Resource | URL |
|----------|-----|
| Web UI | http://localhost:8081/ |
| Swagger | http://localhost:8081/docs |
| Health | http://localhost:8081/api/health |

### Demo API (preloaded records)

```bash
# Generate batch first (optional — demo can bake records at build time)
python scripts/generate_customers.py -n 100 --seed 42

python scripts/run_server.py    # http://localhost:8000
```

### Environment variables (Live)

| Variable | Default | Description |
|----------|---------|-------------|
| `CALLBACK_DELAY_SECONDS` | `3` | Delay between async callbacks (use `120` for spec 2-min think time) |
| `CSV_STORAGE_BACKEND` | `local` | `local` or `s3` |
| `CSV_STORAGE_PATH` | `/data/records/eligibility-records.csv` | Local CSV path |
| `S3_*` | — | S3/MinIO settings when `CSV_STORAGE_BACKEND=s3` |

---

## API Reference

### Live API — primary endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/samples/ee-initiate-request` | Spec sample initiate JSON |
| POST | `/api/eligibility/generate-callbacks?scenario=clean-approval` | **All producers** — raw EE initiate JSON as body |
| POST | `/api/producer/{report_type}` | **Single producer** — body: `{ "scenario", "initiateRequest" }` |
| POST | `/api/journey/initiate` | Async journey (ACK + timed callbacks) |
| GET | `/api/journey/{orcJourneyID}` | Poll journey status |
| GET | `/api/export/csv` | Download accumulated CSV |
| POST | `/api/initiate-request/build` | UI helper: name + DOB + PAN → full initiate |

### Request format

**All producers (`generate-callbacks`):** POST raw EE initiate JSON (from `EE- initiate request V1.0.txt`).

```json
{
  "contextParameter": { "partnerJourneyID", "bankJourneyID", "partnerID", "channelID", "productName" },
  "applicant": {
    "customerDemog": { "name", "dob", "ids": { "panNo" }, ... },
    "bankingDetails": { ... },
    "productDetails": { "multibureau", "perfios", "posidex", "hunter" }
  },
  "coApplicants": { ... },
  "sourceApp": { "constitution": "" }
}
```

- `productDetails` is under **`applicant`**, not at root
- Do **not** include `orcJourneyID` in the initiate request

**Single producer (`/api/producer/mbCibil` etc.):** wrap in:

```json
{ "scenario": "clean-approval", "initiateRequest": { ... } }
```

---

## Sample curl Commands

### Health

```bash
curl -s https://hdfc-eligibility-live-default.apps.ocp.kxxfq.sandbox565.opentlc.com/api/health
```

### All producers (inline EE initiate JSON)

See [`docs/customer/generate-callbacks-curl.sh`](docs/customer/generate-callbacks-curl.sh) or run:

```bash
bash docs/customer/generate-callbacks-curl.sh
```

### CIBIL only

```bash
curl -X POST "https://hdfc-eligibility-live-default.apps.ocp.kxxfq.sandbox565.opentlc.com/api/producer/mbCibil" \
  -H "Content-Type: application/json" \
  -d '{"scenario":"clean-approval","initiateRequest":{...}}'
```

Full inline body is in customer docs / email templates. Sample identity:

| Field | Value |
|-------|-------|
| Name | PRANAV SANTOSH |
| DOB | 1982-09-26 |
| PAN | QAZPC8801X |

### Per-producer paths

| Producer | Path |
|----------|------|
| CIBIL | `/api/producer/mbCibil` |
| Equifax | `/api/producer/mbEquifax` |
| High Mark | `/api/producer/mbHighMark` |
| MB EOT | `/api/producer/mbMbEot` |
| Perfios | `/api/producer/perfios` |
| Posidex | `/api/producer/posidex` |
| Hunter | `/api/producer/hunter` |
| Summary | `/api/producer/summary` |

---

## Scenarios

Configured in `data/scenarios/`. Pass via query `?scenario=` or in request body.

| Scenario | Typical behaviour |
|----------|-------------------|
| `clean-approval` | All producers pass; high CIBIL score |
| `thin-file` | Thin bureau file |
| `fraud-hit` | Hunter match |
| `posidex-match` | Posidex dedupe match |
| `bureau-not-found` | CIBIL subject not found |

---

## Generate Batch Data

```bash
python scripts/generate_customers.py -n 100 --seed 42
```

Output: `data/generated/customers-batch.json` (gitignored)

---

## Validation & Smoke Tests

```bash
# Full spec validation (template fill + constraints)
python scripts/smoke_validate_spec.py

# Template fill audit
python scripts/audit_template_fill.py --strict

# Constraint audit
python scripts/audit_constraints.py
```

Regenerate customer PDF snapshot:

```bash
pip install fpdf2 python-docx   # one-time, for doc scripts
python scripts/generate_customer_snapshot_pdf.py
```

Output: `docs/customer/HDFC_Eligibility_Engine_POC_Snapshot.pdf`

---

## Deploy to OpenShift

### Live API (customer-facing POC)

```bash
oc login
oc project default

oc apply -f openshift/deploy-live.yaml

BUILDER_SECRET=$(oc get sa builder -o jsonpath='{.secrets[?(@.type=="kubernetes.io/dockercfg")].name}')
oc patch buildconfig hdfc-eligibility-live --type=merge \
  -p "{\"spec\":{\"output\":{\"pushSecret\":{\"name\":\"$BUILDER_SECRET\"}}}}"

oc start-build hdfc-eligibility-live --from-dir=. --follow
oc rollout restart deployment/hdfc-eligibility-live

oc get route hdfc-eligibility-live -o jsonpath='https://{.spec.host}{"\n"}'
```

See [`openshift/README-live.md`](openshift/README-live.md) for CSV/S3 storage options.

### Demo API

```bash
oc apply -f openshift/deploy.yaml
oc start-build hdfc-eligibility-engine --from-dir=. --follow
oc rollout restart deployment/hdfc-eligibility-engine
oc get route hdfc-eligibility-engine -o jsonpath='https://{.spec.host}{"\n"}'
```

See [`openshift/README.md`](openshift/README.md) for redeploy steps.

### Docker (local)

```bash
# Live
docker build -f Dockerfile.live -t sdg-api-live .
docker run -p 8080:8080 sdg-api-live

# Demo
docker build -f Dockerfile -t sdg-api-demo .
docker run -p 8080:8080 sdg-api-demo
```

**Note:** `EligibilityEngine_SpecDoc_SampleFiles/` must be included in the image (required at runtime for callback generation).

---

## Spec References

| File | Purpose |
|------|---------|
| `EligibilityEngine_SpecDoc_SampleFiles/EE- initiate request V1.0.txt` | Initiate input JSON |
| `EligibilityEngine_SpecDoc_SampleFiles/EE - Intiate Journey ACK resp.txt` | ACK response |
| `EligibilityEngine_SpecDoc_SampleFiles/* Sample Callback.txt` | Producer callback shapes |
| `EligibilityEngine_SpecDoc_SampleFiles/Requirement_MockAPI.txt` | Mock API requirements |
| `ACE BRE Generic API Spec.pdf` | BRE reference |

---

## Related Documentation

| Document | Location |
|----------|----------|
| Architecture (detailed) | [`docs/EligibilityEngine_Approach_and_Architecture.md`](docs/EligibilityEngine_Approach_and_Architecture.md) |
| Customer snapshot PDF | [`docs/customer/HDFC_Eligibility_Engine_POC_Snapshot.pdf`](docs/customer/HDFC_Eligibility_Engine_POC_Snapshot.pdf) |
| Client Q&A | [`docs/EligibilityEngine_Understanding_and_Client_Questions.txt`](docs/EligibilityEngine_Understanding_and_Client_Questions.txt) |
| OpenShift live deploy | [`openshift/README-live.md`](openshift/README-live.md) |
| OpenShift demo deploy | [`openshift/README.md`](openshift/README.md) |
| Agent / skill index | [`AGENTS.md`](AGENTS.md) |

---

## License & Disclaimer

POC / demo software. Synthetic data only. Not for production credit decisions. Public deployment has no API authentication — harden before any production use.

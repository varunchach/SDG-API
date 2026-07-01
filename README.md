# SDG-API — Eligibility Engine Mock Producer

Synthetic data generator and **mock Producer API** for loan eligibility journey testing. Accepts EE-spec **Initiate Journey** JSON, returns synchronous **ACK**, and generates **producer callbacks** (CIBIL, Equifax, High Mark, Perfios, Posidex, Hunter, Summary).

All data is **synthetic** — no real bureau, Perfios, Posidex, or Hunter integration.

---

## Table of Contents

- [Quick Start (5 minutes)](#quick-start-5-minutes)
- [Which app should I use?](#which-app-should-i-use)
- [Prerequisites](#prerequisites)
- [One-time setup](#one-time-setup)
- [Workflow A — Live API, sync (recommended for integration)](#workflow-a--live-api-sync-recommended-for-integration)
- [Workflow B — Live API, async (spec-like journey)](#workflow-b--live-api-async-spec-like-journey)
- [Workflow C — Live UI (browser)](#workflow-c--live-ui-browser)
- [Workflow D — Demo app (preloaded records)](#workflow-d--demo-app-preloaded-records)
- [API reference](#api-reference)
- [Request format rules](#request-format-rules)
- [Scenarios](#scenarios)
- [Generate batch data](#generate-batch-data)
- [Validation and smoke tests](#validation-and-smoke-tests)
- [Run with Docker (local)](#run-with-docker-local)
- [Deploy to OpenShift](#deploy-to-openshift)
- [Troubleshooting](#troubleshooting)
- [Project structure](#project-structure)
- [Spec references](#spec-references)
- [Related documentation](#related-documentation)

---

## Quick Start (5 minutes)

**Goal:** POST a spec initiate JSON and get ACK + all producer callbacks in one response.

```bash
git clone https://github.com/varunchach/SDG-API.git
cd SDG-API

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-live.txt

uvicorn src.api_live.main:app --host 0.0.0.0 --port 8081
```

In a **second terminal**:

```bash
export BASE_URL=http://localhost:8081

# 1. Health check
curl -s "$BASE_URL/api/health" | jq .

# 2. Fetch the spec sample initiate JSON
curl -s "$BASE_URL/api/samples/ee-initiate-request" | jq . > /tmp/initiate.json

# 3. Generate all producer callbacks (sync)
curl -s -X POST "$BASE_URL/api/eligibility/generate-callbacks?scenario=clean-approval" \
  -H "Content-Type: application/json" \
  -d @/tmp/initiate.json | jq '{orcJourneyID, callbackOrder, ackStatus: .ackResponse.data.statusCode, producers: (.callbacks | keys)}'
```

**Expected output (step 3):** JSON with `orcJourneyID`, `ackResponse`, `callbacks` (one key per producer), and `callbackOrder` listing the order they were generated.

**Or use the bundled script:**

```bash
bash docs/customer/generate-callbacks-curl.sh
# deployed route:
# BASE_URL=https://$(oc get route sdg-eligibility-live -o jsonpath='{.spec.host}') bash docs/customer/generate-callbacks-curl.sh
```

**Swagger UI:** http://localhost:8081/docs

---

## Which app should I use?

This repo ships **two** FastAPI apps. Pick one path and follow it end to end.

| | **Live API** (recommended) | **Demo API** |
|---|---------------------------|--------------|
| **Entry point** | `src/api_live/main.py` | `src/api/main.py` |
| **Local port** | **8081** | **8000** |
| **Docker / OpenShift port** | **8080** | **8080** |
| **Deps file** | `requirements-live.txt` | `requirements.txt` |
| **Customer data** | Generated on the fly (Faker) | Preloaded batch (`generate_customers.py`) |
| **Primary use** | Partner integration testing, public API, CSV export | Internal demo with fixed record list |
| **Sync all callbacks** | `POST /api/eligibility/generate-callbacks` | Not available |
| **Async journey + poll** | `POST /api/journey/initiate` | Same endpoint |
| **Web UI** | http://localhost:8081/ (name/DOB/PAN form) | http://localhost:8000/ (pick from records) |
| **OpenShift manifest** | `openshift/deploy-live.yaml` | `openshift/deploy.yaml` |

**Integration testing?** → Live API, Workflow A or B below.

**Click-through demo with a fixed customer list?** → Demo API, Workflow D below.

---

## Prerequisites

| Tool | Required for |
|------|----------------|
| **Python 3.11+** | Local run |
| **pip** / **venv** | Local run |
| **curl** | API testing |
| **jq** | Pretty-print JSON (recommended) |
| **Docker** | Local container run (optional) |
| **OpenShift CLI (`oc`)** | Cluster deploy (optional) |

---

## One-time setup

```bash
git clone https://github.com/varunchach/SDG-API.git
cd SDG-API

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
```

Install dependencies for the app you will run:

```bash
# Live API (recommended)
pip install -r requirements-live.txt

# Demo API only
pip install -r requirements.txt
```

---

## Workflow A — Live API, sync (recommended for integration)

**When to use:** You have (or will build) a full EE initiate JSON and want **instant** ACK + all producer callbacks in a single HTTP response. No polling.

### Step 1 — Start the server

```bash
source .venv/bin/activate
uvicorn src.api_live.main:app --host 0.0.0.0 --port 8081
```

| Resource | URL |
|----------|-----|
| Web UI | http://localhost:8081/ |
| Swagger | http://localhost:8081/docs |
| Health | http://localhost:8081/api/health |

### Step 2 — Get a valid initiate payload

**Option A — spec sample (easiest):**

```bash
curl -s http://localhost:8081/api/samples/ee-initiate-request | jq . > /tmp/initiate.json
```

**Option B — build from minimal identity:**

```bash
curl -s -X POST http://localhost:8081/api/initiate-request/build \
  -H "Content-Type: application/json" \
  -d '{"name":"PRANAV SANTOSH","dob":"1982-09-26","panNo":"QAZPC8801X","scenario":"clean-approval"}' \
  | jq .initiateRequest > /tmp/initiate.json
```

**Option C — use the file on disk:**

Copy from `EligibilityEngine_SpecDoc_SampleFiles/EE- initiate request V1.0.txt`.

### Step 3 — POST and inspect the response

```bash
curl -s -X POST "http://localhost:8081/api/eligibility/generate-callbacks?scenario=clean-approval" \
  -H "Content-Type: application/json" \
  -d @/tmp/initiate.json | jq .
```

**Response shape:**

```json
{
  "recordId": "SYNC-...",
  "scenario": "clean-approval",
  "orcJourneyID": "ORC-...",
  "initiateRequest": { "...": "..." },
  "ackResponse": { "data": { "statusCode": "0", "statusMessage": "Success" }, "...": "..." },
  "callbacks": {
    "mbCibil": { "reportType": "mbCibil", "...": "..." },
    "mbEquifax": { "...": "..." },
    "summary": { "...": "..." }
  },
  "callbackOrder": ["mbCibil", "mbEquifax", "mbHighMark", "mbMbEot", "perfios", "posidex", "hunter", "summary"],
  "producerHighlights": { "...": "..." }
}
```

### Step 4 — Single producer only

The per-producer endpoint requires a **wrapper** (not raw EE JSON):

```bash
INITIATE=$(curl -s http://localhost:8081/api/samples/ee-initiate-request)

curl -s -X POST http://localhost:8081/api/producer/mbCibil \
  -H "Content-Type: application/json" \
  -d "$(jq -n --argjson ir "$INITIATE" '{scenario:"clean-approval",initiateRequest:$ir}')" \
  | jq '{reportType, orcJourneyID, callbackKeys: (.callback | keys)}'
```

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

## Workflow B — Live API, async (spec-like journey)

**When to use:** You want the **two-phase** flow from the spec — synchronous ACK first, then producer callbacks arrive over time (configurable delay). Matches how a real partner would poll for callbacks.

Default delay: **3 seconds** between callbacks (`CALLBACK_DELAY_SECONDS=3`). Set `120` for the spec's 2-minute think time.

### Step 1 — Start the server

Same as Workflow A (port 8081).

### Step 2 — Submit initiate (async)

```bash
INITIATE=$(curl -s http://localhost:8081/api/samples/ee-initiate-request)

RESP=$(curl -s -X POST http://localhost:8081/api/journey/initiate \
  -H "Content-Type: application/json" \
  -d "$(jq -n --argjson ir "$INITIATE" '{scenario:"clean-approval",initiateRequest:$ir}')")

echo "$RESP" | jq .
ORC=$(echo "$RESP" | jq -r '.orcJourneyID')
echo "orcJourneyID: $ORC"
```

**Immediate response includes:** `orcJourneyID`, `ackResponse`, `callbackOrder`, `callbackDelaySeconds`.

### Step 3 — Poll until COMPLETED

```bash
while true; do
  STATUS=$(curl -s "http://localhost:8081/api/journey/$ORC" | jq -r '.status')
  RECEIVED=$(curl -s "http://localhost:8081/api/journey/$ORC" | jq -r '.callbacksReceived | join(", ")')
  echo "$(date +%H:%M:%S) status=$STATUS  received=[$RECEIVED]"
  [ "$STATUS" = "COMPLETED" ] && break
  sleep 2
done
```

Status progression: `INITIATED` → `IN_PROGRESS` → `COMPLETED`.

With the default 3-second delay and 8 producers, expect **~25 seconds** before `COMPLETED`. Keep polling until status changes.

### Step 4 — Download results

**Full journey JSON:**

```bash
curl -s "http://localhost:8081/api/journey/$ORC/export" | jq . > journey-$ORC.json
```

**Accumulated CSV** (appended after each completed journey):

```bash
curl -s -O -J http://localhost:8081/api/export/csv
# saves eligibility-records.csv
```

### Callback order

Derived from `applicant.productDetails`:

| `productDetails` key | Callbacks (`reportType`) |
|----------------------|--------------------------|
| `multibureau` | mbCibil → mbEquifax → mbHighMark → mbMbEot |
| `perfios` | perfios |
| `posidex` | posidex |
| `hunter` | hunter |
| (always last) | summary |

---

## Workflow C — Live UI (browser)

**When to use:** Quick visual demo without writing curl commands.

### Steps

1. Start the Live API (port 8081):

   ```bash
   uvicorn src.api_live.main:app --host 0.0.0.0 --port 8081
   ```

2. Open http://localhost:8081/

3. Click **Generate Random Customer** — Faker fills the form (name, DOB, PAN, etc.).

4. Edit fields if needed, pick a **scenario** (e.g. `clean-approval`).

5. Click **Run Eligibility Check** — triggers the async journey (ACK + timed callbacks).

6. Watch callbacks appear in the UI as they arrive.

7. When complete, download **CSV** or **journey JSON** from the UI (or use the API endpoints in Workflow B, step 4).

---

## Workflow D — Demo app (preloaded records)

**When to use:** Browse a fixed set of synthetic customers and replay journeys from the demo UI.

### Step 1 — Generate customer batch

```bash
source .venv/bin/activate
pip install -r requirements.txt

python scripts/generate_customers.py -n 100 --seed 42
```

Output: `data/generated/customers-batch.json` (gitignored).

### Step 2 — Start the demo server

```bash
python scripts/run_server.py
# listens on http://localhost:8000
```

Or with uvicorn directly:

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### Step 3 — List and pick a record

```bash
curl -s http://localhost:8000/api/records | jq '.records[:3]'
curl -s http://localhost:8000/api/records/CUST-0001 | jq '.initiateRequest.contextParameter'
```

### Step 4 — Start a journey from a record

```bash
curl -s -X POST "http://localhost:8000/api/journey/initiate/from-record/CUST-0001?scenario=clean-approval" | jq .
```

### Step 5 — Poll (same as Workflow B)

```bash
ORC="<orcJourneyID from step 4>"
curl -s "http://localhost:8000/api/journey/$ORC" | jq '{status, callbacksReceived}'
```

### Step 6 — Use the demo UI

Open http://localhost:8000/ — select a customer from the list and run eligibility check.

---

## API reference

### Live API (`src/api_live/main.py`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health + callback delay + CSV storage info |
| GET | `/api/scenarios` | List valid scenario names |
| GET | `/api/samples/ee-initiate-request` | Spec sample initiate JSON |
| POST | `/api/eligibility/generate-callbacks?scenario=...` | **Sync — all producers** (raw EE JSON or wrapper) |
| POST | `/api/producer/run?scenario=...` | Alias for `generate-callbacks` |
| POST | `/api/producer/{report_type}` | **Sync — single producer** (wrapper required) |
| POST | `/api/initiate-request/build` | Name + DOB + PAN → full initiate JSON |
| POST | `/api/initiate-request/random` | Random full initiate JSON |
| POST | `/api/journey/initiate` | **Async** — ACK now, callbacks over time |
| GET | `/api/journey/{orcJourneyID}` | Poll journey status + received callbacks |
| GET | `/api/journey/{orcJourneyID}/export` | Full journey JSON download |
| GET | `/api/export/csv` | Download accumulated CSV |
| GET | `/api/storage` | CSV backend info (local vs S3) |
| GET | `/` | Live web UI |

### Demo API (`src/api/main.py`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/scenarios` | List scenarios |
| GET | `/api/records` | List preloaded customer IDs |
| GET | `/api/records/{record_id}` | Full customer record |
| POST | `/api/journey/initiate` | Async journey from initiate JSON |
| POST | `/api/journey/initiate/from-record/{record_id}` | Async journey from preloaded record |
| GET | `/api/journey/{orcJourneyID}` | Poll status |
| GET | `/api/journey/{orcJourneyID}/callback/{report_type}` | Fetch one callback |
| GET | `/api/journeys` | List all journeys in memory |
| GET | `/` | Demo web UI |

### Environment variables (Live)

| Variable | Default | Description |
|----------|---------|-------------|
| `CALLBACK_DELAY_SECONDS` | `3` | Seconds between async callbacks (`120` = spec 2-min think time) |
| `CSV_STORAGE_BACKEND` | `local` | `local` or `s3` |
| `CSV_STORAGE_PATH` | `/data/records/eligibility-records.csv` | Local CSV path |
| `S3_ENDPOINT`, `S3_BUCKET`, `S3_OBJECT_KEY`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` | — | S3/MinIO settings when backend is `s3` |
| `PORT` | `8080` (Docker) | Uvicorn port |

---

## Request format rules

These rules apply to **all** initiate payloads:

1. **`productDetails` lives under `applicant`**, not at the root of the JSON.
2. **Do not include `orcJourneyID`** in the initiate request — it is generated at submit time and returned in the ACK.
3. **Top-level keys:** `contextParameter`, `applicant`, `coApplicants`, `sourceApp` (see spec sample file).

**Body format by endpoint:**

| Endpoint | Body format |
|----------|-------------|
| `POST /api/eligibility/generate-callbacks` | Raw EE JSON **or** `{ "initiateRequest": {...}, "scenario": "..." }` |
| `POST /api/producer/{report_type}` | **Wrapper only:** `{ "initiateRequest": {...}, "scenario": "..." }` |
| `POST /api/journey/initiate` | **Wrapper only:** `{ "initiateRequest": {...}, "scenario": "..." }` |

**Spec sample identity** (from `EE- initiate request V1.0.txt`):

| Field | Value |
|-------|-------|
| Name | PRANAV SANTOSH |
| DOB | 1982-09-26 |
| PAN | QAZPC8801X |
| Email | abcdefg@gmail.com |

---

## Scenarios

Pass `?scenario=<name>` on sync endpoints, or include `"scenario"` in the JSON body for async/wrapped calls.

| Scenario | Behaviour |
|----------|-----------|
| `clean-approval` | All producers pass; high CIBIL score |
| `thin-file` | Thin bureau file |
| `fraud-hit` | Hunter match |
| `posidex-match` | Posidex dedupe match |
| `bureau-not-found` | CIBIL subject not found |

List at runtime: `curl -s http://localhost:8081/api/scenarios`

Config files: `data/scenarios/*.json`

---

## Generate batch data

For the demo app or offline inspection:

```bash
python scripts/generate_customers.py -n 100 --seed 42
```

Output:

- `data/generated/customers-batch.json` — all records
- `data/generated/customers/CUST-*.json` — one file per customer

---

## Validation and smoke tests

Run after setup or code changes:

```bash
source .venv/bin/activate
pip install -r requirements-live.txt

python scripts/smoke_validate_spec.py
python scripts/audit_template_fill.py --strict
python scripts/audit_constraints.py
```

Regenerate customer PDF (optional):

```bash
pip install fpdf2 python-docx
python scripts/generate_customer_snapshot_pdf.py
# → docs/customer/SDG_Eligibility_Engine_POC_Snapshot.pdf
```

---

## Run with Docker (local)

### Live API

```bash
docker build -f Dockerfile.live -t sdg-api-live .
docker run -p 8080:8080 sdg-api-live
```

Then use `BASE_URL=http://localhost:8080` for curl commands.

### Demo API

```bash
docker build -f Dockerfile -t sdg-api-demo .
docker run -p 8080:8080 sdg-api-demo
```

The demo image bakes in 10 synthetic records at build time.

**Important:** `EligibilityEngine_SpecDoc_SampleFiles/` must be present in the build context (not excluded by `.dockerignore`).

---

## Deploy to OpenShift

### Prerequisites

```bash
oc login <cluster-url> --token=<your-token>
oc project default          # or: oc new-project sdg-eligibility
```

### Live API (public integration endpoint)

```bash
oc apply -f openshift/deploy-live.yaml

# Required on some clusters so the builder can push the image
BUILDER_SECRET=$(oc get sa builder -o jsonpath='{.secrets[?(@.type=="kubernetes.io/dockercfg")].name}')
oc patch buildconfig sdg-eligibility-live --type=merge \
  -p "{\"spec\":{\"output\":{\"pushSecret\":{\"name\":\"$BUILDER_SECRET\"}}}}"

oc start-build sdg-eligibility-live --from-dir=. --follow
oc rollout restart deployment/sdg-eligibility-live

export BASE_URL=https://$(oc get route sdg-eligibility-live -o jsonpath='{.spec.host}')
echo "$BASE_URL"
```

**Verify:**

```bash
curl -s "$BASE_URL/api/health" | jq .
bash docs/customer/generate-callbacks-curl.sh
```

**CSV storage (default):** local file on PVC at `/data/records/eligibility-records.csv`.

**Optional S3/MinIO:** set env on the Deployment — see [`openshift/README-live.md`](openshift/README-live.md).

### Demo API

```bash
oc apply -f openshift/deploy.yaml
oc start-build sdg-eligibility-engine --from-dir=. --follow
oc rollout restart deployment/sdg-eligibility-engine

export BASE_URL=https://$(oc get route sdg-eligibility-engine -o jsonpath='{.spec.host}')
curl -s "$BASE_URL/api/health"
curl -s "$BASE_URL/api/records" | jq '.records | length'
```

See also: [`openshift/README-live.md`](openshift/README-live.md), [`openshift/README.md`](openshift/README.md).

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `422 Unprocessable Entity` on `/api/producer/mbCibil` | Sent raw EE JSON | Wrap as `{ "scenario": "...", "initiateRequest": {...} }` |
| `400 initiateRequest must not contain orcJourneyID` | `orcJourneyID` in initiate body | Remove it — generated at submit |
| Empty or missing callbacks | `productDetails` at wrong level | Move under `applicant`, not root |
| `404 Record not found` (demo) | No batch generated | Run `python scripts/generate_customers.py -n 100 --seed 42` |
| `404 No CSV file yet` | No completed async journey | Complete Workflow B or C first |
| Port confusion | Local vs Docker/OpenShift | Local Live = **8081**, Docker/OC = **8080** |
| `500` after OpenShift deploy | Spec `.txt` files missing from image | Ensure `.dockerignore` does not exclude `EligibilityEngine_SpecDoc_SampleFiles/` |
| Build push fails on OpenShift | Missing push secret | Run the `BUILDER_SECRET` patch step above |

---

## Project structure

```
SDG-API/
├── src/
│   ├── api/              # Demo FastAPI + journey store
│   ├── api_live/         # Live FastAPI + CSV export
│   ├── generators/       # Faker, templates, spec builder, fillers
│   └── producer/         # Sync producer service + highlights
├── data/
│   ├── scenarios/        # Test behaviour configs
│   └── templates/        # initiate-request, ack, callback JSON templates
├── EligibilityEngine_SpecDoc_SampleFiles/   # Authoritative EE spec samples (.txt)
├── ui/                   # Demo web UI
├── ui_live/              # Live web UI
├── openshift/            # OpenShift manifests (demo + live)
├── scripts/              # Generators, audits, smoke tests
├── docs/                 # Architecture + customer snapshot
├── Dockerfile            # Demo image
├── Dockerfile.live       # Live image
├── requirements.txt      # Demo deps
└── requirements-live.txt # Live deps (+ boto3 for S3 CSV)
```

Architecture diagrams: [`docs/EligibilityEngine_Approach_and_Architecture.md`](docs/EligibilityEngine_Approach_and_Architecture.md)

---

## Spec references

| File | Purpose |
|------|---------|
| `EligibilityEngine_SpecDoc_SampleFiles/EE- initiate request V1.0.txt` | Initiate input JSON |
| `EligibilityEngine_SpecDoc_SampleFiles/EE - Intiate Journey ACK resp.txt` | ACK response |
| `EligibilityEngine_SpecDoc_SampleFiles/* Sample Callback.txt` | Producer callback shapes |
| `EligibilityEngine_SpecDoc_SampleFiles/Requirement_MockAPI.txt` | Mock API requirements |

---

## Related documentation

| Document | Location |
|----------|----------|
| Architecture (diagrams, data model) | [`docs/EligibilityEngine_Approach_and_Architecture.md`](docs/EligibilityEngine_Approach_and_Architecture.md) |
| Customer snapshot PDF | [`docs/customer/SDG_Eligibility_Engine_POC_Snapshot.pdf`](docs/customer/SDG_Eligibility_Engine_POC_Snapshot.pdf) |
| Copy-paste curl (all producers) | [`docs/customer/generate-callbacks-curl.sh`](docs/customer/generate-callbacks-curl.sh) |
| OpenShift live deploy | [`openshift/README-live.md`](openshift/README-live.md) |
| OpenShift demo deploy | [`openshift/README.md`](openshift/README.md) |
| Agent / skill index | [`AGENTS.md`](AGENTS.md) |

---

## License and disclaimer

POC / demo software. Synthetic data only. Not for production credit decisions.

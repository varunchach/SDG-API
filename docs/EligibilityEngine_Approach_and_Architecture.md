# HDFC Eligibility Engine POC — Approach & Architecture

**Purpose:** Mock Producer API for loan eligibility testing — synthetic customer data, EE spec-compliant JSON, and async producer callbacks (CIBIL, Perfios, Posidex, Hunter, Summary).

**Audience:** Client demo, QA, and engineering review.

**Authoritative spec sources:** `EligibilityEngine_SpecDoc_SampleFiles/`, `ACE BRE Generic API Spec.pdf`, `Requirement_MockAPI.txt`

---

## 1. Problem & Approach

### What we simulate

HDFC’s Eligibility Engine sits between a **Partner** (loan origination channel) and multiple **producer systems** (bureau, income, dedupe, fraud). The Partner sends an **Initiate Journey** request; the Engine returns a synchronous **ACK**, then delivers **async callbacks** as each producer completes.

This POC does **not** call real bureaus or bank systems. Instead it:

1. **Accepts** EE-spec initiate JSON (or builds it from minimal identity input).
2. **Generates** synthetic demographics, addresses, IDs, and producer responses.
3. **Keeps one canonical profile** so PAN, name, DOB, and address match across initiate and every callback.
4. **Returns** ACK + timed async callbacks in the order defined by `productDetails`.
5. **Exports** journey results to CSV (live app) for audit and demo replay.

All data is **fake and for testing only**.

### Design principles

| Principle | Implementation |
|-----------|----------------|
| **Spec fidelity** | JSON templates copied verbatim from EE sample files; field names unchanged (`panNo`, `fName`, `APPLICATION-ID`) |
| **Single source of truth** | Internal `profile` object parsed from initiate (or built by Faker); all callbacks filled from it |
| **Scenario-driven behaviour** | `data/scenarios/*.json` overrides scores, Hunter matches, summary pass/fail |
| **Unique synthetic IDs** | `IdentityRegistry` per build; fresh `orcJourneyID` per submit; batch audit for 100-record runs |
| **Two UX modes** | **Demo** — preloaded records; **Live** — identity-first generation on demand |

---

## 2. High-Level Architecture

```mermaid
flowchart TB
    subgraph Partner["Partner / UI"]
        UI_DEMO["Demo UI\n(preloaded records)"]
        UI_LIVE["Live UI\n(Name + DOB + PAN)"]
    end

    subgraph POC["HDFC Eligibility Engine POC"]
        API_DEMO["Demo API\nsrc/api/main.py"]
        API_LIVE["Live API\nsrc/api_live/main.py"]
        GEN["Synthetic Generators\nsrc/generators/"]
        STORE["In-memory Journey Store"]
        CSV["CSV Export\n(PVC or S3/MinIO)"]
    end

    subgraph Outputs["Producer Callbacks (mock)"]
        MB["Multibureau\nmbCibil · mbEquifax · mbHighMark · mbMbEot"]
        PF["Perfios"]
        PX["Posidex"]
        HN["Hunter"]
        SM["Summary"]
    end

    UI_DEMO --> API_DEMO
    UI_LIVE --> API_LIVE
    API_DEMO --> GEN
    API_LIVE --> GEN
    API_DEMO --> STORE
    API_LIVE --> STORE
    API_LIVE --> CSV

    API_DEMO -->|"1 Sync ACK"| Partner
    API_LIVE -->|"1 Sync ACK"| Partner
    STORE -->|"2 Async callbacks"| MB
    STORE --> PF
    STORE --> PX
    STORE --> HN
    STORE --> SM
    MB & PF & PX & HN & SM --> Partner
```

---

## 3. Journey Flow (Runtime)

```mermaid
sequenceDiagram
    autonumber
    participant P as Partner / UI
    participant E as Eligibility Engine
    participant S as Journey Store
    participant C as Callback Dispatcher

    alt Live UI — Build first
        P->>E: POST /api/initiate-request/build<br/>{ name, dob, panNo, scenario }
        E->>E: Faker + IdentityRegistry<br/>→ full initiateRequest
        E-->>P: initiateRequest + generatedDetails
    end

    P->>E: POST /api/journey/initiate<br/>{ initiateRequest, scenario }
    E->>E: profile_from_initiate()<br/>generate orcJourneyID + systemIds
    E->>S: Save LiveJourneyRecord
    E-->>P: Sync ACK (orcJourneyID, statusCode 0)

    loop Every CALLBACK_DELAY_SECONDS
        C->>E: fill template (profile + journey + systemIds)
        C->>S: add_callback(reportType)
        S-->>P: Poll GET /api/journey/{orcJourneyID}
    end

    Note over C,S: Order: mbCibil → mbEquifax → mbHighMark → mbMbEot → perfios → posidex → hunter → summary

    S->>S: status = COMPLETED
    S->>S: append row to CSV (live)
    P->>E: Download CSV / Journey JSON
```

**Callback order** is derived from `applicant.productDetails`:

| `productDetails` key | Callbacks (`reportType`) |
|----------------------|--------------------------|
| `multibureau` | mbCibil, mbEquifax, mbHighMark, mbMbEot |
| `perfios` | perfios |
| `posidex` | posidex |
| `hunter` | hunter |
| (always last) | summary |

Default delay: `CALLBACK_DELAY_SECONDS=3` (configurable; use `120` for spec 2-minute think time).

---

## 4. Live App — Identity-First Approach

The live UI minimises partner input to three fields. Everything else is synthesized while preserving EE JSON structure.

```mermaid
flowchart LR
    subgraph Step1["Step 1 — User input"]
        N[Name]
        D[DOB]
        PAN[PAN]
    end

    subgraph Step2["Step 2 — Build EE Request"]
        B[POST /api/initiate-request/build]
        SYN[Synthetic fill]
        IR[initiateRequest JSON]
    end

    subgraph Step3["Step 3 — Submit & callbacks"]
        SUB[POST /api/journey/initiate]
        ACK[Sync ACK]
        CB[Async producer callbacks]
        DL[Download JSON / CSV]
    end

    N & D & PAN --> B
    B --> SYN
    SYN --> IR
    IR --> SUB
    SUB --> ACK
    ACK --> CB
    CB --> DL
```

### What the user provides vs what is generated

| User provides | Generated synthetically |
|---------------|-------------------------|
| Name (fName / lName) | Address lines 1–4, city, state, pinCode |
| DOB | Age, gender (inferred), email, mobile |
| PAN | customerId, loanAmount, employerName |
| Scenario (behaviour) | partnerJourneyID, bankJourneyID, co-applicant block, productDetails IDs |
| | Perfios txnId in initiate; multibureau IDs at submit |

---

## 5. Data Consistency Model

One internal **profile** drives all producer payloads. Journey **contextParameter** IDs link initiate, ACK, and callbacks.

```mermaid
flowchart TB
    subgraph Input["Initiate Request (INPUT)"]
        ID[Identity: name, DOB, PAN]
        ADDR[Address, mobile, email]
        JID[partnerJourneyID, bankJourneyID]
        PD[productDetails triggers]
    end

    subgraph Internal["Internal canonical objects"]
        PROF["profile"]
        JOUR["journey + orcJourneyID at submit"]
        SYS["systemIds at submit"]
    end

    subgraph Output["Callbacks (OUTPUT)"]
        CIBIL[CIBIL: SCORE, PAN, address]
        PERF[Perfios: grade, salary]
        POS[Posidex: match status]
        HUNT[Hunter: match score]
        SUM[Summary: pass/fail per producer]
    end

    ID & ADDR --> PROF
    JID --> JOUR
    PD --> JOUR
    JOUR --> SYS

    PROF --> CIBIL & PERF & POS
    JOUR --> CIBIL & PERF & POS & HUNT & SUM
    SYS --> CIBIL & PERF & POS & HUNT
```

### ID lifecycle

| ID | When assigned | Consistency rule |
|----|---------------|------------------|
| `partnerJourneyID`, `bankJourneyID` | Build (live) or batch generate | Same in initiate, ACK, all callbacks |
| `orcJourneyID` | **Submit only** (not in initiate per spec) | Same in ACK + all callbacks |
| `customerId`, PAN, mobile, email | Build | Applicant ≠ co-applicant; PAN from user in live flow |
| Multibureau applicationId, tracking IDs | Submit | One set per journey, reused across bureau callbacks |
| Perfios `perfiosTransactionId` | Build (in initiate) | Callback reads from initiate `productDetails` |

**Uniqueness:** `IdentityRegistry` prevents duplicate PAN, mobile, email, customerId, and journey IDs within a single build. Each **Build** uses a new timestamp seed. Each **Submit** generates a new `orcJourneyID` (UUID + timestamp). Batch script (`generate_customers.py -n 100`) runs a cross-record audit.

---

## 6. Software Component Map

```
HDFC_Bank_POC/
├── EligibilityEngine_SpecDoc_SampleFiles/   # Authoritative JSON samples
├── data/
│   ├── templates/                           # Copied spec templates for fillers
│   └── scenarios/                           # Behaviour overrides (5 scenarios)
├── src/
│   ├── generators/                          # Core synthetic data engine
│   │   ├── customer.py                      # Profile + journey context
│   │   ├── live_record.py                   # Build initiate from identity
│   │   ├── spec_builder.py                  # initiateRequest + ackResponse
│   │   ├── template_filler.py               # All producer callbacks
│   │   ├── system_ids.py                    # Journey & bureau ID generators
│   │   ├── uniqueness.py                    # IdentityRegistry
│   │   └── validate.py                      # Cross-payload PAN/score checks
│   ├── api/                                 # Demo API + initiate parser
│   │   ├── main.py
│   │   └── initiate_parser.py               # initiate → profile + journey
│   └── api_live/                            # Live API + CSV export
│       ├── main.py
│       ├── journey_service.py               # Async callback dispatch
│       └── csv_export.py
├── ui/                                      # Demo UI (preloaded records)
├── ui_live/                                 # Live UI (identity-first)
├── scripts/generate_customers.py            # Batch: 100 records CLI
├── openshift/
│   ├── deploy.yaml                          # Demo deployment
│   └── deploy-live.yaml                     # Live deployment + PVC
└── docs/                                    # This document
```

### Generation pipeline (batch / internal)

```
scenario → Faker identity → IdentityRegistry → system IDs
    → fill spec template (initiate + ACK + callbacks) → validate_record()
```

---

## 7. Deployment Architecture (OpenShift)

Two independent deployments share generator code but serve different use cases.

```mermaid
flowchart TB
    subgraph OCP["OpenShift Cluster"]
        subgraph Demo["Demo App"]
            RD["Route: hdfc-eligibility-engine"]
            DD["Deployment + Image\n50 records baked in"]
        end
        subgraph Live["Live App"]
            RL["Route: hdfc-eligibility-live"]
            DL["Deployment + PVC\n/data/records/"]
        end
        BC1["BuildConfig: hdfc-eligibility-engine"]
        BC2["BuildConfig: hdfc-eligibility-live"]
    end

    User1[Client demo] --> RD --> DD
    User2[Live testing] --> RL --> DL
    BC1 --> DD
    BC2 --> DL
```

| App | Image / Dockerfile | UI | Data |
|-----|-------------------|-----|------|
| **Demo** | `Dockerfile` | `ui/` — pick preloaded record | 50 records at build time |
| **Live** | `Dockerfile.live` | `ui_live/` — Name + DOB + PAN | On-the-fly generate + CSV on PVC |

**Live URLs (sandbox example):**

- Demo: `https://hdfc-eligibility-engine-default.apps.ocp.8v2x7.sandbox1891.opentlc.com`
- Live: `https://hdfc-eligibility-live-default.apps.ocp.8v2x7.sandbox1891.opentlc.com`

**Local run:**

```bash
# Demo
.venv/bin/python scripts/run_server.py          # http://localhost:8000

# Live
.venv/bin/pip install -r requirements-live.txt
.venv/bin/uvicorn src.api_live.main:app --port 8080
```

---

## 8. Scenarios (Test Behaviours)

Files in `data/scenarios/` control producer outcomes without changing JSON shape:

| Scenario | Typical use |
|----------|----------------|
| `clean-approval` | All producers pass; high CIBIL score |
| `bureau-not-found` | CIBIL subject not found |
| `low-score-decline` | Low bureau score |
| `fraud-hit` | Hunter match |
| `partial-failure` | Mixed pass/fail in summary |

Selected in the Live UI before **Build EE Request**; passed through to callback fillers.

---

## 9. API Summary (Live)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/initiate-request/build` | Name + DOB + PAN → full `initiateRequest` |
| POST | `/api/journey/initiate` | Submit initiate → ACK + start callbacks |
| GET | `/api/journey/{orcJourneyID}` | Poll status + received callbacks |
| GET | `/api/export/csv` | Download accumulated results CSV |
| GET | `/api/journey/{orcJourneyID}/export` | Download full journey JSON |

---

## 10. What Is In Scope vs Out of Scope

| In scope | Out of scope |
|----------|--------------|
| EE spec JSON structure for initiate, ACK, callbacks | Real bureau / Perfios / Hunter integration |
| Synthetic Faker `en_IN` identity and addresses | Production-grade persistence (DB) |
| Identity consistency across producers | Global cross-session ID registry (optional future) |
| CSV export of journey outcomes | Real credit decisions |
| OpenShift deploy for demo + live | ACE BRE rule engine execution |

---

## 11. Related Documents

| Document | Location |
|----------|----------|
| Client Q&A / understanding | `docs/EligibilityEngine_Understanding_and_Client_Questions.txt` |
| Field schemas | `.cursor/skills/hdfc-eligibility-engine/schemas.md` |
| Generator → spec mappings | `.cursor/skills/hdfc-eligibility-engine/mappings.md` |
| OpenShift deploy (demo) | `openshift/README.md` |
| OpenShift deploy (live) | `openshift/README-live.md` |
| Agent entry point | `AGENTS.md` |

---

*Last updated: June 2026 — reflects Live UI identity-first flow, download endpoints, and dual OpenShift deployment.*

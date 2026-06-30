# Generators — Code & CLI

Faker `en_IN` + custom PAN/mobile rules. **No LLM.**

---

## Setup

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/generate_customers.py -n 100 --seed 42
```

| Flag | Default | Purpose |
|------|---------|---------|
| `-n` | 100 | Record count |
| `-s` | 42 | Random seed (reproducible) |
| `-o` | `data/generated` | Output dir |

---

## Modules (`src/generators/`)

| File | Exports | Role |
|------|---------|------|
| `indian_identity.py` | `unique_pan`, `generate_indian_mobile`, `pick_indian_name`, `pick_location` | PAN `AAAAA9999A`, mobile 6–9 prefix |
| `system_ids.py` | `generate_journey_ids`, `generate_orc_journey_id`, `generate_system_ids` | Journey + per-producer IDs |
| `customer.py` | `generate_customer_profile`, `generate_journey_context`, `generate_customer_record`, `generate_customer_batch` | Full record assembly |

---

## Current output shape (Phase 1a)

```json
{
  "recordId": "CUST-0001",
  "scenario": "clean-approval",
  "profile": { "firstName", "pan", "dob", ... },
  "journey": { "orcJourneyID", "productDetails", ... },
  "systemIds": { "multibureau", "perfios", "posidex", "hunter" }
}
```

**Phase 1b target** — see [schemas.md](schemas.md):

```json
{
  "recordId", "scenario",
  "initiateRequest": {},
  "ackResponse": {},
  "callbacks": { "mbCibil", "mbEquifax", "mbHighMark", "mbMbEot", "perfios", "posidex", "hunter", "summary" }
}
```

Use [mappings.md](mappings.md) to transform `profile`/`journey`/`systemIds` → spec JSON.

---

## Scenarios (`data/scenarios/*.json`)

Override **behaviour only** (scores, matches, errors). Identity stays from `profile`.

```json
{
  "name": "clean-approval",
  "mbCibil": { "score": "742", "subjectReturnCode": "FOUND" },
  "hunter": { "matches": "0", "totalMatchScore": "0" }
}
```

Built-in scenarios in `customer.py`: `clean-approval`, `thin-file`, `fraud-hit`, `posidex-match`, `bureau-not-found`.

---

## Phase 1b–1c implementation steps

1. Add `src/generators/spec_builder.py` — build `initiateRequest` + `ackResponse` from profile/journey using mappings.md
2. Copy spec samples → `data/templates/callbacks/*.json` (structure only, placeholder values)
3. Add `src/generators/template_filler.py` — deep-fill templates from profile + systemIds + scenario
4. Validate output keys against spec samples; values against [constraints.md](constraints.md)

---

## Rules

- Same `pan` / name / DOB in every callback for one record
- `orcJourneyID` only in ACK + callbacks, not initiate
- Copy spec JSON structure verbatim — change values only
- `--seed 42` for deterministic test data

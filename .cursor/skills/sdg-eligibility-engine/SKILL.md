---
name: sdg-eligibility-engine
description: >-
  SDG Eligibility Engine mock producer — schemas, constraints, field mappings,
  Faker generators. Use for initiate/callback payloads, MB, Perfios, Posidex,
  Hunter, or API work in SDG-API.
---

# Eligibility Engine — Mock Producer

Partner sends Initiate → Engine returns ACK → async producer callbacks → Summary.
Build synthetic data with **one consistent fake customer** across all systems.

## Read order

| # | File | Use when |
|---|------|----------|
| 1 | [schemas.md](schemas.md) | JSON shape — input/output per producer |
| 2 | [constraints.md](constraints.md) | Valid values, types, ranges |
| 3 | [mappings.md](mappings.md) | Generator fields → spec JSON paths |
| 4 | [generators.md](generators.md) | Run/extend Python code |

## Authoritative sources (do not invent)

| Source | Path | For |
|--------|------|-----|
| EE spec samples | `EligibilityEngine_SpecDoc_SampleFiles/` | Exact JSON structure |
| ACE BRE v1.1 | `ACE BRE Generic API Spec.pdf` | Types/lengths (not Perfios) |
| Mock API req | `Requirement_MockAPI.txt` | Async flow, 2min think time |
| Scenarios | `data/scenarios/*.json` | Score/match overrides |

## Spec sample index

| File | Role |
|------|------|
| `EE- initiate request V1.0.txt` | Initiate input |
| `EE - Intiate Journey ACK resp.txt` | Sync ACK success |
| `EE-Sample Failure.txt` | Sync ACK failure |
| `mbCibil Sample Callback.txt` | reportType: mbCibil |
| `mbEquifax Sample Callback.txt` | reportType: mbEquifax |
| `mbHighMark Sample Callback.txt` | reportType: mbHighMark |
| `mbMbEot Sample Callback.txt` | reportType: mbMbEot |
| `perfios Sample Callback.txt` | perfios body (add envelope) |
| `posidex Sample Callback.txt` | reportType: posidex |
| `hunter Sample Callback.txt` | reportType: hunter |
| `summary Sample Callback.txt` | reportType: summary (last) |

## Repo layout

```
EligibilityEngine_SpecDoc_SampleFiles/   # copy as templates
ACE BRE Generic API Spec.pdf
.cursor/skills/sdg-eligibility-engine/  # this skill
src/generators/                          # Faker code
scripts/generate_customers.py
data/scenarios/                          # behaviour overrides
data/generated/                          # output (gitignored; run generate script)
docs/                                    # client Q&A doc
```

## Run

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/generate_customers.py -n 100 --seed 42
```

Output: `data/generated/` (gitignored)

## Phases

| Phase | Status |
|-------|--------|
| 1a | Done — generators + 100 records |
| 1b | Next — spec-format initiate + ACK |
| 1c | Pending — callback templates + filler |
| 2–3 | Pending — storage + API |

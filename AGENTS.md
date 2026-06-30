# SDG-API — Eligibility Engine

Synthetic data tool + mock Producer API for loan eligibility testing.

## Start here

All instructions live in `.cursor/skills/hdfc-eligibility-engine/`:

| File | Contents |
|------|----------|
| `SKILL.md` | Entry, spec index, build phases |
| `schemas.md` | Input/output JSON per producer |
| `constraints.md` | Valid values & ranges (spec / ACE BRE / gen) |
| `mappings.md` | Generator → spec field paths |
| `generators.md` | CLI, modules, implementation steps |

External refs: `EligibilityEngine_SpecDoc_SampleFiles/`, `ACE BRE Generic API Spec.pdf`

**Approach & architecture:** `docs/EligibilityEngine_Approach_and_Architecture.md`

## Run (local)

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/generate_customers.py -n 100 --seed 42
.venv/bin/python scripts/run_server.py   # http://localhost:8000
```

Output: `data/generated/` (gitignored — run script to create)

## Run (OpenShift)

```bash
oc apply -f openshift/deploy.yaml
oc start-build sdg-eligibility-engine --from-dir=. --follow
oc get route sdg-eligibility-engine -o jsonpath='https://{.spec.host}{"\n"}'
```

See `openshift/README.md` for redeploy steps.

## Phases

| Phase | Status |
|-------|--------|
| 1a–1c | Done — generators, spec initiate/ACK, callbacks |
| 2–3 | Done — in-memory store + FastAPI + UI (OpenShift deploy) |

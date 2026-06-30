# Live generator — on-the-fly customers + CSV export

Separate from the demo app (`sdg-eligibility-engine`). Demo deployment is untouched.

## Deploy

```bash
oc apply -f openshift/deploy-live.yaml
BUILDER_SECRET=$(oc get sa builder -o jsonpath='{.secrets[?(@.type=="kubernetes.io/dockercfg")].name}')
oc patch buildconfig sdg-eligibility-live --type=merge \
  -p "{\"spec\":{\"output\":{\"pushSecret\":{\"name\":\"$BUILDER_SECRET\"}}}}"
oc start-build sdg-eligibility-live --from-dir=. --follow
oc rollout restart deployment/sdg-eligibility-live
oc get route sdg-eligibility-live -o jsonpath='https://{.spec.host}{"\n"}'
```

## CSV storage

**Default (deployed):** local CSV on PVC at `/data/records/eligibility-records.csv`

**MinIO / S3:** set env on Deployment:

| Env | Example |
|-----|---------|
| `CSV_STORAGE_BACKEND` | `s3` |
| `S3_ENDPOINT` | `http://minio.minio.svc:9000` |
| `S3_BUCKET` | `eligibility-records` |
| `S3_OBJECT_KEY` | `eligibility-records.csv` |
| `S3_ACCESS_KEY` | your key |
| `S3_SECRET_KEY` | your secret |

## UI flow

1. **Generate Random Customer** — Faker fills form (no preloaded batch)
2. Edit fields if needed
3. **Run Eligibility Check** — same initiate → ACK → async callbacks pipeline
4. On completion → row appended to CSV

## Local run

```bash
.venv/bin/pip install -r requirements-live.txt
.venv/bin/uvicorn src.api_live.main:app --port 8081
# open http://localhost:8081
```

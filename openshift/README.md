# OpenShift deployment

## Live URL

After deploy, get the route:

```bash
oc get route sdg-eligibility-engine -o jsonpath='https://{.spec.host}{"\n"}'
```

## First-time deploy

```bash
oc login   # already done
oc project default   # or: oc new-project sdg-eligibility
oc apply -f openshift/deploy.yaml
oc start-build sdg-eligibility-engine --from-dir=. --follow
oc rollout restart deployment/sdg-eligibility-engine
```

## Redeploy after code changes

```bash
oc start-build sdg-eligibility-engine --from-dir=. --follow
oc rollout restart deployment/sdg-eligibility-engine
```

## Notes

- App runs **uvicorn** on port **8080** (Python ASGI server).
- **FastAPI** is the web framework in `src/api/main.py` — it is part of the app code, not a separate product to install on OpenShift.
- `CALLBACK_DELAY_SECONDS` env controls async callback spacing (default `3`; set `120` for spec 2-minute think time).
- Image build generates 50 synthetic customer records baked into the container.

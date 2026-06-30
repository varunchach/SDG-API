"""Append eligibility journey rows to CSV — local file or S3/MinIO."""

from __future__ import annotations

import csv
import io
import os
from datetime import datetime, timezone
from typing import Any

CSV_COLUMNS = [
    "savedAt",
    "recordId",
    "scenario",
    "orcJourneyID",
    "partnerJourneyID",
    "bankJourneyID",
    "panNo",
    "fullName",
    "dob",
    "gender",
    "email",
    "mobile",
    "city",
    "state",
    "pinCode",
    "loanAmount",
    "cibilScore",
    "hunterMatches",
    "posidexStatus",
    "summaryMbCibil",
    "summaryMbEquifax",
    "summaryMbHighMark",
    "summaryPerfios",
    "summaryPosidex",
    "summaryHunter",
]

STORAGE_BACKEND = os.environ.get("CSV_STORAGE_BACKEND", "local").lower()
LOCAL_CSV_PATH = os.environ.get(
    "CSV_STORAGE_PATH",
    "/data/records/eligibility-records.csv",
)
S3_BUCKET = os.environ.get("S3_BUCKET", "eligibility-records")
S3_KEY = os.environ.get("S3_OBJECT_KEY", "eligibility-records.csv")
S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "")
S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY", "")
S3_REGION = os.environ.get("S3_REGION", "us-east-1")


def _row_from_journey(rec: Any) -> dict[str, str]:
    profile = rec.profile
    summary = rec.callbacks.get("summary", {}).get("applicant", {}).get("summary", {})
    cibil_domain = (
        rec.callbacks.get("mbCibil", {})
        .get("mbCibil", {})
        .get("Body", {})
        .get("MultiBureauResponse", {})
        .get("RESPONSE", {})
        .get("FINISHED", {})
        .get("JSON-RESPONSE-OBJECT", {})
        .get("CIBIL_SROP_DOMAIN_LIST", [{}])[0]
    )
    hunter = (
        rec.callbacks.get("hunter", {})
        .get("hunter", {})
        .get("Body", {})
        .get("MatchResponse", {})
        .get("MatchResult", {})
        .get("ResultBlock", {})
        .get("MatchSummary", {})
    )
    pos_rows = rec.callbacks.get("posidex", {}).get("posidex", {}).get("outputdata", [])
    return {
        "savedAt": datetime.now(timezone.utc).isoformat(),
        "recordId": rec.record_id,
        "scenario": rec.scenario,
        "orcJourneyID": rec.orc_journey_id,
        "partnerJourneyID": rec.partner_journey_id,
        "bankJourneyID": rec.bank_journey_id,
        "panNo": profile["pan"],
        "fullName": profile["fullName"],
        "dob": profile["dob"],
        "gender": profile["gender"],
        "email": profile["email"],
        "mobile": profile["mobile"],
        "city": profile["city"],
        "state": profile["state"],
        "pinCode": profile["pinCode"],
        "loanAmount": profile["loanAmount"],
        "cibilScore": str(cibil_domain.get("SCORE", "")),
        "hunterMatches": str(hunter.get("matches", "")),
        "posidexStatus": pos_rows[0].get("SOA_STATUS_C", "") if pos_rows else "",
        "summaryMbCibil": summary.get("mbCibil", ""),
        "summaryMbEquifax": summary.get("mbEquifax", ""),
        "summaryMbHighMark": summary.get("mbHighMark", ""),
        "summaryPerfios": summary.get("perfios", ""),
        "summaryPosidex": summary.get("posidex", ""),
        "summaryHunter": summary.get("hunter", ""),
    }


def _append_csv_bytes(existing: bytes, row: dict[str, str]) -> bytes:
    buf = io.StringIO()
    if existing:
        text = existing.decode("utf-8")
        buf.write(text)
        if not text.endswith("\n"):
            buf.write("\n")
    else:
        writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writerow(row)
    return buf.getvalue().encode("utf-8")


def _s3_client():
    import boto3
    from botocore.client import Config

    kwargs: dict[str, Any] = {
        "service_name": "s3",
        "aws_access_key_id": S3_ACCESS_KEY,
        "aws_secret_access_key": S3_SECRET_KEY,
        "region_name": S3_REGION,
        "config": Config(signature_version="s3v4"),
    }
    if S3_ENDPOINT:
        kwargs["endpoint_url"] = S3_ENDPOINT
    return boto3.client(**kwargs)


def _append_s3(row: dict[str, str]) -> str:
    from botocore.exceptions import ClientError

    client = _s3_client()
    existing = b""
    try:
        obj = client.get_object(Bucket=S3_BUCKET, Key=S3_KEY)
        existing = obj["Body"].read()
    except ClientError as exc:
        if exc.response["Error"]["Code"] not in ("NoSuchKey", "404"):
            raise
    payload = _append_csv_bytes(existing, row)
    client.put_object(Bucket=S3_BUCKET, Key=S3_KEY, Body=payload, ContentType="text/csv")
    return f"s3://{S3_BUCKET}/{S3_KEY}"


def _append_local(row: dict[str, str]) -> str:
    os.makedirs(os.path.dirname(LOCAL_CSV_PATH), exist_ok=True)
    existing = b""
    if os.path.exists(LOCAL_CSV_PATH):
        with open(LOCAL_CSV_PATH, "rb") as f:
            existing = f.read()
    payload = _append_csv_bytes(existing, row)
    with open(LOCAL_CSV_PATH, "wb") as f:
        f.write(payload)
    return LOCAL_CSV_PATH


def append_journey_to_csv(rec: Any) -> dict[str, str]:
    row = _row_from_journey(rec)
    if STORAGE_BACKEND == "s3":
        location = _append_s3(row)
    else:
        location = _append_local(row)
    return {"storageBackend": STORAGE_BACKEND, "location": location, "recordId": rec.record_id}


def storage_info() -> dict[str, str]:
    if STORAGE_BACKEND == "s3":
        return {
            "backend": "s3",
            "bucket": S3_BUCKET,
            "objectKey": S3_KEY,
            "endpoint": S3_ENDPOINT or "(default AWS)",
        }
    return {"backend": "local", "path": LOCAL_CSV_PATH}


def local_csv_path() -> str:
    """Path to local CSV file (empty if using S3 backend)."""
    if STORAGE_BACKEND == "s3":
        return ""
    return LOCAL_CSV_PATH

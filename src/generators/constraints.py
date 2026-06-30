"""Spec/BRE field constraints — valid ranges and formats for generated values."""

from __future__ import annotations

import re
from typing import Any

PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
MOBILE_RE = re.compile(r"^[6-9]\d{9}$")
PIN_RE = re.compile(r"^\d{6}$")
NUMERIC_STR_RE = re.compile(r"^-?\d+$")
DECIMAL_12_2_RE = re.compile(r"^-?\d{1,10}(\.\d{1,2})?$")

VALID_GENDERS = frozenset({"M", "F"})
VALID_GENDER_CIBIL = frozenset({"MALE", "FEMALE"})
VALID_GENDER_HIGHMARK = frozenset({"Male", "Female"})
VALID_SUBJECT_RETURN = frozenset({"FOUND", "NOT FOUND"})
VALID_SOA_STATUS = frozenset({"Match", "No Match"})
VALID_SUMMARY_STATUS = frozenset({"Success", "Failed", "Late", "Not Opted"})
VALID_STATUS_CODE = frozenset({"0", "1"})
VALID_Y_N = frozenset({"Y", "N"})
VALID_SENT_TO = frozenset({"Y", "N"})

# BRE / spec string max lengths (constraints.md)
BRE_MAX_LEN: dict[str, int] = {
    "CONSUMER_NAME_FIELD1": 100,
    "ID_NUMBER": 100,
    "MEMBER_REFERENCE_NUMBER": 100,
    "SCORE": 100,
    "ERRORMSG": 1000,
    "NAME_IQ": 100,
    "PAN_IQ": 100,
    "EMAIL_1_IQ": 100,
    "PHONE_1_IQ": 100,
    "SOA_FNAME_C": 1000,
    "FILLER_35": 1000,
    "SOA_STATUS_C": 1000,
    "address": 10000,
    "ADDRESS_LINE_1": 200,
    "ADDRESS_LINE_2": 200,
    "ADDRESS_1_IQ": 200,
    "ADDRESS_2_IQ": 200,
}

# Scenario-specific operational ranges
HUNTER_SCORE_RANGES: dict[str, tuple[int, int]] = {
    "clean-approval": (0, 100),
    "thin-file": (0, 100),
    "bureau-not-found": (0, 100),
    "posidex-match": (0, 100),
    "fraud-hit": (800, 1200),
}

CIBIL_SCORE_BY_SCENARIO: dict[str, set[str]] = {
    "thin-file": {"-1"},
}

PARTNER_JOURNEY_LEN = (10, 12)
BANK_JOURNEY_LEN = (10, 12)
AGE_RANGE = (21, 65)


def _field_name(path: str) -> str:
    return path.split(".")[-1].split("[")[0]


def _check_len(path: str, value: str, errors: list[str], label: str) -> None:
    field = _field_name(path)
    limit = BRE_MAX_LEN.get(field)
    if limit is not None and len(value) > limit:
        errors.append(f"{label}: {path} length {len(value)} > {limit}")


def _walk_leaves(obj: Any, prefix: str = "") -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []
    if isinstance(obj, dict):
        for key, val in obj.items():
            child = f"{prefix}.{key}" if prefix else key
            rows.extend(_walk_leaves(val, child))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            rows.extend(_walk_leaves(item, f"{prefix}[{i}]"))
    else:
        rows.append((prefix, obj))
    return rows


def validate_journey_constraints(journey: dict[str, Any], errors: list[str], label: str) -> None:
    partner = journey.get("partnerJourneyID", "")
    bank = journey.get("bankJourneyID", "")
    orc_id = journey.get("orcJourneyID", "")
    product = journey.get("productName", "")

    if not partner.isdigit() or not (PARTNER_JOURNEY_LEN[0] <= len(partner) <= PARTNER_JOURNEY_LEN[1]):
        errors.append(f"{label}: partnerJourneyID out of range (10–12 digits): {partner!r}")
    if not bank.isdigit() or not (BANK_JOURNEY_LEN[0] <= len(bank) <= BANK_JOURNEY_LEN[1]):
        errors.append(f"{label}: bankJourneyID out of range (10–12 digits): {bank!r}")
    if product and not orc_id.startswith(f"{product}_WF_"):
        errors.append(f"{label}: orcJourneyID must start with {product}_WF_")


def validate_system_ids(system_ids: dict[str, Any], errors: list[str], label: str) -> None:
    mb = system_ids.get("multibureau", {})
    for key in ("applicationId", "custId", "acknowledgementId"):
        val = mb.get(key, "")
        if val and not val.isdigit():
            errors.append(f"{label}: multibureau.{key} must be numeric: {val!r}")
    for bureau, tid in mb.get("trackingIds", {}).items():
        if tid and not tid.isdigit():
            errors.append(f"{label}: trackingIds.{bureau} must be numeric: {tid!r}")

    perf = system_ids.get("perfios", {})
    ptxn = perf.get("perfiosTransactionId", "")
    if ptxn and not ptxn.startswith("KKH"):
        errors.append(f"{label}: perfiosTransactionId must start with KKH: {ptxn!r}")

    pos = system_ids.get("posidex", {})
    if pos.get("soaAppId") and not pos["soaAppId"].isdigit():
        errors.append(f"{label}: posidex.soaAppId must be numeric")


def validate_profile_constraints(profile: dict[str, Any], errors: list[str], label: str) -> None:
    pan = profile.get("pan", "")
    if pan and not PAN_RE.match(pan):
        errors.append(f"{label}: invalid PAN format: {pan!r}")
    mobile = profile.get("mobile", "")
    if mobile and not MOBILE_RE.match(mobile):
        errors.append(f"{label}: invalid mobile (10 digits, 6–9 start): {mobile!r}")
    pin = profile.get("pinCode", "")
    if pin and not PIN_RE.match(pin):
        errors.append(f"{label}: invalid pinCode (6 digits): {pin!r}")
    gender = profile.get("gender", "")
    if gender and gender not in VALID_GENDERS:
        errors.append(f"{label}: gender must be M or F: {gender!r}")
    try:
        age = int(profile.get("age", "0"))
        if not (AGE_RANGE[0] <= age <= AGE_RANGE[1]):
            errors.append(f"{label}: age {age} outside {AGE_RANGE[0]}–{AGE_RANGE[1]}")
    except ValueError:
        errors.append(f"{label}: age must be numeric")


def validate_callback_values(
    callbacks: dict[str, Any],
    scenario_name: str,
    errors: list[str],
    label: str,
) -> None:
    hunter_range = HUNTER_SCORE_RANGES.get(scenario_name, (0, 500))

    for path, raw in _walk_leaves(callbacks):
        if raw is None or raw == "":
            continue
        if not isinstance(raw, str):
            continue

        field = _field_name(path)
        _check_len(path, raw, errors, label)

        if field in ("ID_NUMBER", "PAN_IQ", "FILLER_35", "pan") and len(raw) == 10:
            if not PAN_RE.match(raw):
                errors.append(f"{label}: invalid PAN at {path}: {raw!r}")
        if field in ("mobile", "FILLER_40", "PHONE_1_IQ") and raw.isdigit() and len(raw) == 10:
            if not MOBILE_RE.match(raw):
                errors.append(f"{label}: invalid mobile at {path}: {raw!r}")
        if field in ("PINCODE", "FILLER_12", "FILLER_29", "FILLER_45") and raw.isdigit() and len(raw) == 6:
            if not PIN_RE.match(raw):
                errors.append(f"{label}: invalid pin at {path}: {raw!r}")
        if field == "SUBJECT_RETURN_CODE" and raw not in VALID_SUBJECT_RETURN:
            errors.append(f"{label}: invalid SUBJECT_RETURN_CODE: {raw!r}")
        if field == "SOA_STATUS_C" and raw not in VALID_SOA_STATUS:
            errors.append(f"{label}: invalid SOA_STATUS_C: {raw!r}")
        elif field == "SOA_STATUS_C" and scenario_name == "posidex-match" and "outputdata[0]" in path and raw != "Match":
            errors.append(f"{label}: posidex-match primary row requires SOA_STATUS_C = Match")
        elif field == "SOA_STATUS_C" and scenario_name == "clean-approval" and "outputdata[0]" in path and raw != "No Match":
            errors.append(f"{label}: clean-approval primary row requires SOA_STATUS_C = No Match")
        if field == "SCORE" and "CIBIL_SROP_DOMAIN_LIST" in path:
            if not NUMERIC_STR_RE.match(raw):
                errors.append(f"{label}: SCORE must be numeric string: {raw!r}")
            elif scenario_name in CIBIL_SCORE_BY_SCENARIO:
                if raw not in CIBIL_SCORE_BY_SCENARIO[scenario_name]:
                    errors.append(
                        f"{label}: scenario {scenario_name} expects SCORE "
                        f"in {CIBIL_SCORE_BY_SCENARIO[scenario_name]}, got {raw!r}"
                    )
            elif scenario_name == "clean-approval":
                try:
                    score_val = int(raw)
                    if score_val != -1 and not (300 <= score_val <= 900):
                        errors.append(f"{label}: CIBIL SCORE {score_val} outside typical range 300–900")
                except ValueError:
                    pass
        if field == "GENDER" and "CIBIL" in path.upper() and raw not in VALID_GENDER_CIBIL:
            errors.append(f"{label}: invalid CIBIL GENDER: {raw!r}")
        if field == "GENDER_IQ" and raw not in VALID_GENDER_HIGHMARK:
            errors.append(f"{label}: invalid HighMark GENDER_IQ: {raw!r}")
        if field == "TotalMatchScore":
            if not raw.isdigit():
                errors.append(f"{label}: TotalMatchScore must be numeric: {raw!r}")
            else:
                score = int(raw)
                lo, hi = hunter_range
                if not (lo <= score <= hi):
                    errors.append(
                        f"{label}: TotalMatchScore {score} outside scenario range {lo}–{hi}"
                    )
        if field == "matches" and not raw.isdigit():
            errors.append(f"{label}: hunter matches must be numeric: {raw!r}")
        elif field == "matches" and scenario_name == "fraud-hit" and path.endswith("MatchSummary.matches"):
            if int(raw) < 1:
                errors.append(f"{label}: fraud-hit scenario requires matches >= 1")
        elif field == "matches" and scenario_name == "clean-approval" and path.endswith("MatchSummary.matches"):
            if int(raw) != 0:
                errors.append(f"{label}: clean-approval scenario requires matches = 0")
        if field == "perfiosTransactionId" and not raw.startswith("KKH"):
            errors.append(f"{label}: perfiosTransactionId must start with KKH: {raw!r}")
        if any(token in field for token in ("AMT", "AMOUNT", "DISBURSED", "INSTALLMENT", "SALARY")):
            if "." in raw and not DECIMAL_12_2_RE.match(raw):
                errors.append(f"{label}: amount out of decimal(12,2) range at {path}: {raw!r}")

    summary = callbacks.get("summary", {})
    for key, value in summary.get("applicant", {}).get("summary", {}).items():
        if value not in VALID_SUMMARY_STATUS:
            errors.append(f"{label}: summary.applicant.{key} invalid status: {value!r}")

    for key in ("statusCode",):
        for rtype, cb in callbacks.items():
            if isinstance(cb, dict) and key in cb and cb[key] not in VALID_STATUS_CODE:
                errors.append(f"{label}: {rtype}.statusCode must be 0 or 1: {cb[key]!r}")


def validate_record_constraints(record: dict[str, Any]) -> list[str]:
    """Return constraint violations for a full generated record."""
    errors: list[str] = []
    label = record.get("recordId", "record")
    scenario = record.get("scenario", "clean-approval")

    validate_profile_constraints(record.get("profile", {}), errors, label)
    validate_journey_constraints(record.get("journey", {}), errors, label)
    validate_system_ids(record.get("systemIds", {}), errors, label)
    validate_callback_values(record.get("callbacks", {}), scenario, errors, label)
    return errors

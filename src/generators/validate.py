"""Validate generated records against spec templates and constraints."""

from __future__ import annotations

import re
from typing import Any

from .constraints import validate_record_constraints
from .json_utils import keys_match, load_template

PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
MOBILE_RE = re.compile(r"^[6-9]\d{9}$")
PIN_RE = re.compile(r"^\d{6}$")
VALID_GENDERS = frozenset({"M", "F"})
VALID_SUMMARY_STATUS = frozenset({"Success", "Failed", "Late", "Not Opted"})
VALID_REPORT_TYPES = frozenset({
    "mbCibil", "mbEquifax", "mbHighMark", "mbMbEot",
    "perfios", "posidex", "hunter", "summary",
})
# Fields we populate but are not in the EE initiate sample template
OPTIONAL_INITIATE_DEMOG_KEYS = frozenset({"mobile"})


def _check_pan(pan: str, errors: list[str], label: str) -> None:
    if not PAN_RE.match(pan):
        errors.append(f"{label}: invalid PAN format: {pan}")


def _check_identity_consistency(record: dict[str, Any], errors: list[str]) -> None:
    pan = record["initiateRequest"]["applicant"]["customerDemog"]["ids"]["panNo"]
    name = record["initiateRequest"]["applicant"]["customerDemog"]["name"][0]
    full_name = " ".join(p for p in (name["fName"], name.get("mName", ""), name["lName"]) if p)
    dob = record["initiateRequest"]["applicant"]["customerDemog"]["dob"]

    _check_pan(pan, errors, "initiate.panNo")

    cibil = record["callbacks"]["mbCibil"]
    cibil_domain = cibil["mbCibil"]["Body"]["MultiBureauResponse"]["RESPONSE"]["FINISHED"][
        "JSON-RESPONSE-OBJECT"
    ]["CIBIL_SROP_DOMAIN_LIST"][0]
    if cibil_domain["ID_NUMBER"] != pan:
        errors.append("mbCibil ID_NUMBER != initiate panNo")
    if cibil_domain["CONSUMER_NAME_FIELD1"] != full_name:
        errors.append("mbCibil name != initiate name")

    perf_pan = record["callbacks"]["perfios"]["perfios"]["CustomerInfo"]["pan"]
    if perf_pan != pan:
        errors.append("perfios pan != initiate panNo")

    pos_rows = record["callbacks"]["posidex"]["posidex"]["outputdata"]
    if pos_rows and pos_rows[0].get("FILLER_35") != pan:
        errors.append("posidex FILLER_35 != initiate panNo")

    if dob and "-" in dob:
        expected_cibil_dob = f"{dob[8:10]}{dob[5:7]}{dob[0:4]}"
        if cibil_domain["DATE_OF_BIRTH"] != expected_cibil_dob:
            errors.append("mbCibil DATE_OF_BIRTH != initiate dob (DDMMYYYY)")


def _check_journey_ids(record: dict[str, Any], errors: list[str]) -> None:
    journey = record["journey"]
    ack = record["ackResponse"]["data"]
    if ack["orcJourneyID"] != journey["orcJourneyID"]:
        errors.append("ACK orcJourneyID mismatch")
    if ack["partnerJourneyID"] != journey["partnerJourneyID"]:
        errors.append("ACK partnerJourneyID mismatch")

    for rtype in ("mbCibil", "mbEquifax", "mbHighMark", "mbMbEot", "perfios", "posidex", "hunter"):
        ctx = record["callbacks"][rtype]["contextParameter"]
        if ctx["orcJourneyID"] != journey["orcJourneyID"]:
            errors.append(f"{rtype} orcJourneyID mismatch")
        if ctx["partnerJourneyID"] != journey["partnerJourneyID"]:
            errors.append(f"{rtype} partnerJourneyID mismatch")

    initiate_ctx = record["initiateRequest"]["contextParameter"]
    if "orcJourneyID" in initiate_ctx:
        errors.append("initiateRequest must not contain orcJourneyID")


def _check_profile_constraints(profile: dict[str, Any], errors: list[str]) -> None:
    _check_pan(profile["pan"], errors, "profile.pan")
    if profile["gender"] not in VALID_GENDERS:
        errors.append(f"invalid gender: {profile['gender']}")
    if not MOBILE_RE.match(profile["mobile"]):
        errors.append(f"invalid mobile: {profile['mobile']}")
    if not PIN_RE.match(profile["pinCode"]):
        errors.append(f"invalid pinCode: {profile['pinCode']}")


def _check_summary(record: dict[str, Any], errors: list[str]) -> None:
    summary = record["callbacks"]["summary"]
    if summary.get("userType") is not None or summary.get("userIndex") is not None:
        errors.append("summary must not have userType/userIndex")
    for key, value in summary["applicant"]["summary"].items():
        if value not in VALID_SUMMARY_STATUS:
            errors.append(f"summary.applicant.{key}: invalid status '{value}'")


def _check_template_keys(record: dict[str, Any], errors: list[str]) -> None:
    init_t = load_template("initiate-request")
    # Co-applicant array length may differ; compare applicant subtree keys
    init_gen = record["initiateRequest"]
    errors.extend(keys_match(init_t["contextParameter"], init_gen["contextParameter"], label="initiate.context"))
    applicant_t = init_t["applicant"]
    applicant_g = init_gen["applicant"]
    demog_g = applicant_g.get("customerDemog", {})
    demog_filtered = {
        k: v for k, v in demog_g.items() if k not in OPTIONAL_INITIATE_DEMOG_KEYS
    }
    applicant_g_filtered = {**applicant_g, "customerDemog": demog_filtered}
    errors.extend(keys_match(applicant_t, applicant_g_filtered, label="initiate.applicant"))

    ack_t = load_template("ack-response")
    errors.extend(keys_match(ack_t, record["ackResponse"], label="ack"))

    for rtype in VALID_REPORT_TYPES:
        if rtype == "perfios":
            t_body = load_template("perfios-body")
            g_body = record["callbacks"]["perfios"]["perfios"]
            errors.extend(keys_match(t_body, g_body, label="perfios.body"))
            g_cb = record["callbacks"]["perfios"]
            for key in ("contextParameter", "statusCode", "statusMsg", "userType", "userIndex", "reportType", "perfios"):
                if key not in g_cb:
                    errors.append(f"perfios.envelope: missing key {key}")
            if g_cb.get("reportType") != "perfios":
                errors.append("perfios.envelope: reportType must be perfios")
        elif rtype == "summary":
            t = load_template("summary")
            g = record["callbacks"]["summary"]
            errors.extend(keys_match(
                {k: v for k, v in t.items() if k != "coApplicants"},
                {k: v for k, v in g.items() if k != "coApplicants"},
                label="summary",
            ))
        else:
            t = load_template(rtype)
            g = record["callbacks"][rtype]
            if rtype == "posidex":
                t_row = t["posidex"]["outputdata"][0]
                g_rows = g["posidex"]["outputdata"]
                if g_rows:
                    errors.extend(keys_match(t_row, g_rows[0], label="posidex.row"))
                t_env = {k: v for k, v in t.items() if k != "posidex"}
                g_env = {k: v for k, v in g.items() if k != "posidex"}
                errors.extend(keys_match(t_env, g_env, label="posidex.envelope"))
            else:
                errors.extend(keys_match(t, g, label=rtype))


def validate_record(record: dict[str, Any]) -> list[str]:
    """Return list of validation errors (empty = valid)."""
    errors: list[str] = []
    _check_profile_constraints(record["profile"], errors)
    _check_identity_consistency(record, errors)
    _check_journey_ids(record, errors)
    _check_summary(record, errors)
    _check_template_keys(record, errors)
    errors.extend(validate_record_constraints(record))
    return errors

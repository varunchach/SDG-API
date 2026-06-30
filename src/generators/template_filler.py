"""Fill callback templates from profile, journey, systemIds, and scenario overrides."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .callback_formats import dob_to_cibil, dob_to_highmark, gender_cibil, gender_highmark
from .json_utils import deep_copy, load_template, set_path
from .nonempty_filler import apply_nonempty_fills, make_fill_context
from .spec_templates import load_spec_callback


def _fill_context_envelope(
    cb: dict[str, Any],
    journey: dict[str, Any],
    *,
    report_type: str,
    include_orc: bool = True,
) -> None:
    set_path(cb, "contextParameter.partnerJourneyID", journey["partnerJourneyID"])
    set_path(cb, "contextParameter.bankJourneyID", journey["bankJourneyID"])
    if include_orc:
        set_path(cb, "contextParameter.orcJourneyID", journey["orcJourneyID"])
    set_path(cb, "contextParameter.partnerID", journey["partnerID"])
    set_path(cb, "contextParameter.channelID", journey["channelID"])
    set_path(cb, "contextParameter.productName", journey["productName"])
    set_path(cb, "statusCode", "0")
    set_path(cb, "statusMsg", "Success")
    set_path(cb, "reportType", report_type)
    if report_type != "summary":
        set_path(cb, "userType", "applicant")
        set_path(cb, "userIndex", "0")


def _mb_header_paths(report_key: str) -> str:
    return f"{report_key}.Body.MultiBureauResponse.RESPONSE"


def _complete_from_template(
    generated: dict[str, Any],
    template_name: str,
    producer: str,
    profile: dict[str, Any],
    journey: dict[str, Any],
    system_ids: dict[str, Any],
    scenario: dict[str, Any],
) -> None:
    template = load_spec_callback(template_name)
    ctx = make_fill_context(producer, profile, journey, system_ids, scenario)
    apply_nonempty_fills(generated, template, ctx)


def fill_mb_cibil(
    profile: dict[str, Any],
    journey: dict[str, Any],
    system_ids: dict[str, Any],
    scenario: dict[str, Any],
) -> dict[str, Any]:
    cb = deep_copy(load_template("mbCibil"))
    _fill_context_envelope(cb, journey, report_type="mbCibil")

    mb = system_ids["multibureau"]
    sc = scenario.get("mbCibil", {})
    base = _mb_header_paths("mbCibil")
    set_path(cb, f"{base}.HEADER.APPLICATION-ID", mb["applicationId"])
    set_path(cb, f"{base}.HEADER.CUST-ID", mb["custId"])
    set_path(cb, f"{base}.ACKNOWLEDGEMENT-ID", mb["acknowledgementId"])
    set_path(cb, f"{base}.FINISHED.TRACKING-ID", mb["trackingIds"]["mbCibil"])

    domain = f"{base}.FINISHED.JSON-RESPONSE-OBJECT.CIBIL_SROP_DOMAIN_LIST[0]"
    set_path(cb, f"{domain}.MEMBER_REFERENCE_NUMBER", mb["custId"])
    set_path(cb, f"{domain}.SUBJECT_RETURN_CODE", sc.get("subjectReturnCode", "FOUND"))
    set_path(cb, f"{domain}.SCORE", sc.get("score", "742"))
    set_path(cb, f"{domain}.CONSUMER_NAME_FIELD1", profile["fullName"])
    set_path(cb, f"{domain}.DATE_OF_BIRTH", dob_to_cibil(profile["dob"]))
    set_path(cb, f"{domain}.GENDER", gender_cibil(profile["gender"]))
    set_path(cb, f"{domain}.ID_NUMBER", profile["pan"])
    set_path(cb, f"{domain}.ADDRESS_LINE_1", profile["addressLine1"])
    set_path(cb, f"{domain}.ADDRESS_LINE_2", profile["addressLine2"])
    set_path(cb, f"{domain}.PINCODE", profile["pinCode"])
    set_path(cb, f"{domain}.STATE", profile["state"])
    _complete_from_template(cb, "mbCibil", "mbCibil", profile, journey, system_ids, scenario)
    return cb


def fill_mb_equifax(
    profile: dict[str, Any],
    journey: dict[str, Any],
    system_ids: dict[str, Any],
    scenario: dict[str, Any],
) -> dict[str, Any]:
    cb = deep_copy(load_template("mbEquifax"))
    _fill_context_envelope(cb, journey, report_type="mbEquifax")

    mb = system_ids["multibureau"]
    sc = scenario.get("mbEquifax", {})
    base = _mb_header_paths("mbEquifax")
    set_path(cb, f"{base}.HEADER.APPLICATION-ID", mb["applicationId"])
    set_path(cb, f"{base}.HEADER.CUST-ID", mb["custId"])
    set_path(cb, f"{base}.ACKNOWLEDGEMENT-ID", mb["acknowledgementId"])
    set_path(cb, f"{base}.FINISHED.TRACKING-ID", mb["trackingIds"]["mbEquifax"])

    error_msg = sc.get("errorMsg", "SUCCESS") or "SUCCESS"
    domain_list = get_equifax_domain_list(cb)
    for i in range(len(domain_list)):
        set_path(
            cb,
            f"{base}.FINISHED.JSON-RESPONSE-OBJECT.EQUIFAX_EROP_DOMAIN_LIST[{i}].MEMBER_REFERENCE_NUMBER",
            mb["custId"],
        )
        set_path(
            cb,
            f"{base}.FINISHED.JSON-RESPONSE-OBJECT.EQUIFAX_EROP_DOMAIN_LIST[{i}].ERRORMSG",
            error_msg,
        )
    _complete_from_template(cb, "mbEquifax", "mbEquifax", profile, journey, system_ids, scenario)
    return cb


def get_equifax_domain_list(cb: dict[str, Any]) -> list:
    return cb["mbEquifax"]["Body"]["MultiBureauResponse"]["RESPONSE"]["FINISHED"][
        "JSON-RESPONSE-OBJECT"
    ]["EQUIFAX_EROP_DOMAIN_LIST"]


def fill_mb_highmark(
    profile: dict[str, Any],
    journey: dict[str, Any],
    system_ids: dict[str, Any],
    scenario: dict[str, Any],
) -> dict[str, Any]:
    cb = deep_copy(load_template("mbHighMark"))
    _fill_context_envelope(cb, journey, report_type="mbHighMark")

    mb = system_ids["multibureau"]
    sc = scenario.get("mbHighMark", {})
    base = _mb_header_paths("mbHighMark")
    set_path(cb, f"{base}.HEADER.APPLICATION-ID", mb["applicationId"])
    set_path(cb, f"{base}.HEADER.CUST-ID", mb["custId"])
    set_path(cb, f"{base}.ACKNOWLEDGEMENT-ID", mb["acknowledgementId"])
    set_path(cb, f"{base}.FINISHED.TRACKING-ID", mb["trackingIds"]["mbHighMark"])

    iq = f"{base}.FINISHED.JSON-RESPONSE-OBJECT.CHM_BASE_SROP_DOMAIN_LIST[0].CHM_BASE_SROP_DOMAIN_LIST1"
    set_path(cb, f"{iq}.MEMBER_REFERENCE_NUMBER", mb["custId"])
    set_path(cb, f"{iq}.STATUS_IQ", sc.get("statusIq", "SUCCESS"))
    set_path(cb, f"{iq}.NAME_IQ", profile["fullName"])
    set_path(cb, f"{iq}.PAN_IQ", profile["pan"])
    set_path(cb, f"{iq}.DOB_IQ", dob_to_highmark(profile["dob"]))
    set_path(cb, f"{iq}.GENDER_IQ", gender_highmark(profile["gender"]))
    set_path(cb, f"{iq}.LOS_APP_ID_IQ", mb["applicationId"])
    set_path(cb, f"{iq}.MBR_ID_IQ", mb["custId"])
    set_path(cb, f"{iq}.PHONE_1_IQ", profile["mobile"])
    set_path(cb, f"{iq}.EMAIL_1_IQ", profile["email"])
    _complete_from_template(cb, "mbHighMark", "mbHighMark", profile, journey, system_ids, scenario)
    return cb


def fill_mb_mbeot(
    journey: dict[str, Any],
    system_ids: dict[str, Any],
    scenario: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cb = deep_copy(load_template("mbMbEot"))
    _fill_context_envelope(cb, journey, report_type="mbMbEot")

    eot = system_ids["multibureau"]["eot"]
    base = "mbMbEot.Body.MultiBureauEoTRequest"
    set_path(cb, f"{base}.HEADER.APPLICATION-ID", eot["applicationId"])
    set_path(cb, f"{base}.HEADER.CUST-ID", eot["custId"])
    set_path(cb, f"{base}.ACKNOWLEDGEMENT-ID", eot["acknowledgementId"])
    set_path(cb, f"{base}.STATUS", "END-OF-TXN")
    set_path(cb, f"{base}.SENT-TO-CIBIL", eot["sentToCibil"])
    set_path(cb, f"{base}.SENT-TO-EQUIFAX", eot["sentToEquifax"])
    set_path(cb, f"{base}.SENT-TO-EXPERIAN", eot["sentToExperian"])
    set_path(cb, f"{base}.SENT-TO-CHM", eot["sentToChm"])
    _complete_from_template(
        cb,
        "mbMbEot",
        "mbMbEot",
        {},
        journey,
        system_ids,
        scenario or {},
    )
    return cb


def fill_perfios(
    profile: dict[str, Any],
    journey: dict[str, Any],
    system_ids: dict[str, Any],
    scenario: dict[str, Any],
) -> dict[str, Any]:
    body = deep_copy(load_template("perfios-body"))
    sc = scenario.get("perfios", {})
    perf = system_ids["perfios"]

    address = f"{profile['addressLine1']}, {profile['city']}, {profile['state']} {profile['pinCode']}"
    set_path(body, "CustomerInfo.pan", profile["pan"])
    set_path(body, "CustomerInfo.name", profile["fullName"])
    set_path(body, "CustomerInfo.email", profile["email"])
    set_path(body, "CustomerInfo.mobile", profile["mobile"])
    set_path(body, "CustomerInfo.perfiosTransactionId", journey["productDetails"]["perfios"]["perfiosTransactionId"])
    set_path(body, "CustomerInfo.customerTransactionId", perf["customerTransactionId"])
    set_path(body, "CustomerInfo.address", address)
    set_path(body, "AdditionalParameters.employerName", profile["employerName"])
    set_path(body, "SummaryInfo.grade", sc.get("grade", "AAA"))
    set_path(body, "SummaryInfo.medianSalary", sc.get("medianSalary", "40750"))
    set_path(body, "Statementdetails.Statement.CustomerInfo.pan", profile["pan"])
    set_path(body, "Statementdetails.Statement.CustomerInfo.name", profile["fullName"])
    set_path(body, "Statementdetails.Statement.CustomerInfo.email", profile["email"])
    set_path(body, "Statementdetails.Statement.CustomerInfo.mobile", profile["mobile"])
    set_path(body, "Statementdetails.Statement.CustomerInfo.address", address)

    cb: dict[str, Any] = {
        "contextParameter": {},
        "statusCode": "",
        "statusMsg": "",
        "userType": "",
        "userIndex": "",
        "reportType": "",
        "perfios": body,
    }
    _fill_context_envelope(cb, journey, report_type="perfios")
    ctx = make_fill_context("perfios", profile, journey, system_ids, scenario)
    apply_nonempty_fills(cb["perfios"], load_template("perfios-body"), ctx)
    apply_nonempty_fills(cb, {
        "contextParameter": {
            "partnerJourneyID": "x",
            "bankJourneyID": "x",
            "orcJourneyID": "x",
            "partnerID": "x",
            "channelID": "x",
            "productName": "x",
        },
        "statusCode": "0",
        "statusMsg": "Success",
        "userType": "applicant",
        "userIndex": "0",
        "reportType": "perfios",
    }, ctx)
    return cb


def fill_posidex(
    profile: dict[str, Any],
    journey: dict[str, Any],
    system_ids: dict[str, Any],
    scenario: dict[str, Any],
) -> dict[str, Any]:
    cb = deep_copy(load_spec_callback("posidex"))
    _fill_context_envelope(cb, journey, report_type="posidex")

    sc = scenario.get("posidex", {})
    pos = system_ids["posidex"]
    soa_status = sc.get("soaStatus", "No Match")
    rows = cb["posidex"]["outputdata"]
    if rows:
        _fill_posidex_row(rows[0], profile, pos, soa_status, row_index=0)
    _complete_from_template(cb, "posidex", "posidex", profile, journey, system_ids, scenario)
    return cb


def _fill_posidex_row(
    row: dict[str, Any],
    profile: dict[str, Any],
    pos: dict[str, Any],
    soa_status: str,
    *,
    row_index: int = 0,
) -> None:
    row["SOA_APP_ID_C"] = pos["soaAppId"]
    row["FILLER_35"] = profile["pan"]
    row["SOA_FNAME_C"] = profile["fullName"]
    row["SOA_LNAME_C"] = profile["lastName"]
    row["SOA_MNAME_C"] = profile.get("middleName", "")
    match_ids = pos.get("soaMatchAppIds", [])
    if row_index > 0 and row_index - 1 < len(match_ids):
        row["SOA_MATCH_APPID_C"] = match_ids[row_index - 1]
    elif match_ids:
        row["SOA_MATCH_APPID_C"] = match_ids[0]
    row["SOA_STATUS_C"] = soa_status
    row["SOA_MATCH_PARAMETER"] = "NAME,PAN"
    row["FILLER_31"] = "NAME,PAN"
    row["FILLER_40"] = profile["mobile"]
    row["FILLER_2"] = profile["city"]
    row["FILLER_22"] = profile["state"]
    row["FILLER_29"] = profile["pinCode"]
    row["SOA_DEDUPE_DATE"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S.0")


def fill_hunter(
    journey: dict[str, Any],
    system_ids: dict[str, Any],
    scenario: dict[str, Any],
    profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cb = deep_copy(load_template("hunter"))
    _fill_context_envelope(cb, journey, report_type="hunter")

    sc = scenario.get("hunter", {})
    hunter_ids = system_ids["hunter"]
    matches = sc.get("matches", hunter_ids["matches"])
    score = sc.get("totalMatchScore", hunter_ids["totalMatchScore"])

    base = "hunter.Body.MatchResponse.MatchResult.ResultBlock.MatchSummary"
    set_path(cb, f"{base}.matches", matches)
    set_path(cb, f"{base}.TotalMatchScore", score)
    _complete_from_template(
        cb,
        "hunter",
        "hunter",
        profile or {},
        journey,
        system_ids,
        scenario,
    )
    return cb


def _derive_mb_cibil_status(cb: dict[str, Any]) -> str:
    domain = cb["mbCibil"]["Body"]["MultiBureauResponse"]["RESPONSE"]["FINISHED"][
        "JSON-RESPONSE-OBJECT"
    ]["CIBIL_SROP_DOMAIN_LIST"][0]
    if domain.get("SUBJECT_RETURN_CODE") == "NOT FOUND":
        return "Failed"
    return "Success"


def _derive_mb_equifax_status(cb: dict[str, Any]) -> str:
    items = cb["mbEquifax"]["Body"]["MultiBureauResponse"]["RESPONSE"]["FINISHED"][
        "JSON-RESPONSE-OBJECT"
    ]["EQUIFAX_EROP_DOMAIN_LIST"]
    for item in items:
        msg = (item.get("ERRORMSG") or "").lower()
        if "not found" in msg:
            return "Failed"
    return "Success"


def _derive_summary_statuses(
    callbacks: dict[str, Any],
    scenario: dict[str, Any],
) -> dict[str, str]:
    return {
        "mbCibil": _derive_mb_cibil_status(callbacks["mbCibil"]),
        "mbEquifax": _derive_mb_equifax_status(callbacks["mbEquifax"]),
        "mbHighMark": "Success",
        "mbEot": "Success",
        "mbMergedScore": "Not Opted",
        "mbExperian": "Not Opted",
        "mbCriflite": "Not Opted",
        "perfios": "Success",
        "posidex": "Success",
        "hunter": "Success",
    }


def fill_summary(
    journey: dict[str, Any],
    callbacks: dict[str, Any],
    scenario: dict[str, Any],
    *,
    co_applicant_count: int = 0,
) -> dict[str, Any]:
    cb = deep_copy(load_spec_callback("summary"))
    _fill_context_envelope(cb, journey, report_type="summary", include_orc=False)

    statuses = _derive_summary_statuses(callbacks, scenario)
    template_co = cb["coApplicants"]["coApplicantArray"]
    co_slots = max(co_applicant_count, len(template_co))

    _complete_from_template(cb, "summary", "summary", {}, journey, {}, scenario)

    for key, value in statuses.items():
        set_path(cb, f"applicant.summary.{key}", value)

    set_path(cb, "coApplicants.totalCoApplicants", str(co_slots))
    co_array = []
    for i in range(1, co_slots + 1):
        co_array.append({"index": str(i), "summary": dict(statuses)})
    set_path(cb, "coApplicants.coApplicantArray", co_array)
    for i in range(co_slots):
        for key, value in statuses.items():
            set_path(cb, f"coApplicants.coApplicantArray[{i}].summary.{key}", value)
    return cb


def fill_all_callbacks(
    profile: dict[str, Any],
    journey: dict[str, Any],
    system_ids: dict[str, Any],
    scenario: dict[str, Any],
    *,
    co_applicant_count: int = 0,
) -> dict[str, Any]:
    """Fill all producer callbacks and summary."""
    callbacks: dict[str, Any] = {}
    callbacks["mbCibil"] = fill_mb_cibil(profile, journey, system_ids, scenario)
    callbacks["mbEquifax"] = fill_mb_equifax(profile, journey, system_ids, scenario)
    callbacks["mbHighMark"] = fill_mb_highmark(profile, journey, system_ids, scenario)
    callbacks["mbMbEot"] = fill_mb_mbeot(journey, system_ids, scenario)
    callbacks["perfios"] = fill_perfios(profile, journey, system_ids, scenario)
    callbacks["posidex"] = fill_posidex(profile, journey, system_ids, scenario)
    callbacks["hunter"] = fill_hunter(journey, system_ids, scenario)
    callbacks["summary"] = fill_summary(
        journey, callbacks, scenario, co_applicant_count=co_applicant_count
    )
    return callbacks

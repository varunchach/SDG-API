"""Extract popular producer callback fields for UI investigation panels."""

from __future__ import annotations

from typing import Any

PRODUCER_TITLES: dict[str, str] = {
    "mbCibil": "mbCibil (CIBIL)",
    "mbEquifax": "mbEquifax",
    "mbHighMark": "mbHighMark (CRIF High Mark)",
    "mbMbEot": "mbMbEot (Multibureau EOT)",
    "perfios": "Perfios",
    "posidex": "Posidex",
    "hunter": "Hunter",
    "summary": "Summary",
}


def _row(
    label: str,
    initiate: str,
    output: str,
    *,
    match: bool | None = None,
) -> dict[str, Any]:
    return {
        "label": label,
        "initiate": initiate,
        "output": output,
        "match": match,
    }


def _pack(report_type: str, fields: list[dict[str, Any]]) -> dict[str, Any]:
    matched = sum(1 for f in fields if f["match"] is True)
    comparable = sum(1 for f in fields if f["match"] is not None)
    return {
        "reportType": report_type,
        "title": PRODUCER_TITLES.get(report_type, report_type),
        "fields": fields,
        "matchedCount": matched,
        "comparableCount": comparable,
    }


def _initiate_identity(initiate_request: dict[str, Any]) -> dict[str, Any]:
    demog = initiate_request["applicant"]["customerDemog"]
    name = demog["name"][0]
    addr = demog["address"][0]
    full_name = " ".join(p for p in (name["fName"], name.get("mName", ""), name["lName"]) if p)
    dob = demog["dob"]
    return {
        "fullName": full_name,
        "firstName": name["fName"],
        "lastName": name["lName"],
        "middleName": name.get("mName", ""),
        "pan": demog["ids"]["panNo"],
        "dob": dob,
        "gender": demog.get("gender", ""),
        "email": demog.get("emailId1", ""),
        "mobile": demog.get("mobile", ""),
        "address1": addr.get("address1", ""),
        "address2": addr.get("address2", ""),
        "city": addr.get("city", ""),
        "state": addr.get("state", ""),
        "pinCode": addr.get("pinCode", ""),
        "employer": initiate_request["applicant"].get("employmentDetails", {}).get("employerName", ""),
        "loanAmount": initiate_request["applicant"]["bankingDetails"]["loanDetails"]["loanAmount"],
        "customerId": initiate_request["applicant"]["bankingDetails"]["accountInfo"][0].get("customerId", ""),
        "partnerJourneyID": initiate_request["contextParameter"].get("partnerJourneyID", ""),
        "bankJourneyID": initiate_request["contextParameter"].get("bankJourneyID", ""),
        "cibilDob": f"{dob[8:10]}{dob[5:7]}{dob[0:4]}" if dob and "-" in dob else "",
        "highmarkDob": f"{dob[8:10]}-{dob[5:7]}-{dob[0:4]}" if dob and "-" in dob else "",
        "perfiosAddress": f"{addr.get('address1', '')}, {addr.get('city', '')}, {addr.get('state', '')} {addr.get('pinCode', '')}",
    }



def _context_rows(initiate_request: dict[str, Any], callback: dict[str, Any]) -> list[dict[str, Any]]:
    idn = _initiate_identity(initiate_request)
    ctx = callback.get("contextParameter", {})
    return [
        _row(
            "partnerJourneyID",
            idn["partnerJourneyID"],
            ctx.get("partnerJourneyID", ""),
            match=ctx.get("partnerJourneyID", "") == idn["partnerJourneyID"],
        ),
        _row(
            "bankJourneyID",
            idn["bankJourneyID"],
            ctx.get("bankJourneyID", ""),
            match=ctx.get("bankJourneyID", "") == idn["bankJourneyID"],
        ),
        _row("orcJourneyID", "assigned at submit", ctx.get("orcJourneyID", "")),
        _row("partnerID", initiate_request["contextParameter"].get("partnerID", ""), ctx.get("partnerID", "")),
        _row("channelID", initiate_request["contextParameter"].get("channelID", ""), ctx.get("channelID", "")),
        _row("productName", initiate_request["contextParameter"].get("productName", ""), ctx.get("productName", "")),
    ]


def extract_mb_cibil_highlights(initiate_request: dict[str, Any], callback: dict[str, Any]) -> dict[str, Any]:
    idn = _initiate_identity(initiate_request)
    domain = (
        callback.get("mbCibil", {})
        .get("Body", {})
        .get("MultiBureauResponse", {})
        .get("RESPONSE", {})
        .get("FINISHED", {})
        .get("JSON-RESPONSE-OBJECT", {})
        .get("CIBIL_SROP_DOMAIN_LIST", [{}])[0]
    )
    header = (
        callback.get("mbCibil", {})
        .get("Body", {})
        .get("MultiBureauResponse", {})
        .get("RESPONSE", {})
        .get("HEADER", {})
    )
    finished = (
        callback.get("mbCibil", {})
        .get("Body", {})
        .get("MultiBureauResponse", {})
        .get("RESPONSE", {})
        .get("FINISHED", {})
    )
    fields = [
        _row("Consumer name", idn["fullName"], domain.get("CONSUMER_NAME_FIELD1", ""), match=domain.get("CONSUMER_NAME_FIELD1", "") == idn["fullName"]),
        _row("PAN / ID number", idn["pan"], domain.get("ID_NUMBER", ""), match=domain.get("ID_NUMBER", "") == idn["pan"]),
        _row("Date of birth", idn["dob"], domain.get("DATE_OF_BIRTH", ""), match=domain.get("DATE_OF_BIRTH", "") == idn["cibilDob"]),
        _row("Gender", idn["gender"], domain.get("GENDER", "")),
        _row("CIBIL score", "—", domain.get("SCORE", "")),
        _row("Subject return code", "—", domain.get("SUBJECT_RETURN_CODE", "")),
        _row("Address line 1", idn["address1"], domain.get("ADDRESS_LINE_1", ""), match=domain.get("ADDRESS_LINE_1", "") == idn["address1"]),
        _row("Pincode", idn["pinCode"], domain.get("PINCODE", ""), match=domain.get("PINCODE", "") == idn["pinCode"]),
        _row("State", idn["state"], domain.get("STATE", ""), match=domain.get("STATE", "") == idn["state"]),
        _row("Application ID", "—", header.get("APPLICATION-ID", "")),
        _row("Multibureau cust ID", "—", header.get("CUST-ID", "")),
        _row("Tracking ID", "—", finished.get("TRACKING-ID", "")),
        *_context_rows(initiate_request, callback),
    ]
    return _pack("mbCibil", fields)


def extract_mb_equifax_highlights(initiate_request: dict[str, Any], callback: dict[str, Any]) -> dict[str, Any]:
    idn = _initiate_identity(initiate_request)
    base = (
        callback.get("mbEquifax", {})
        .get("Body", {})
        .get("MultiBureauResponse", {})
        .get("RESPONSE", {})
    )
    header = base.get("HEADER", {})
    finished = base.get("FINISHED", {})
    items = finished.get("JSON-RESPONSE-OBJECT", {}).get("EQUIFAX_EROP_DOMAIN_LIST", [{}])
    item = items[0] if items else {}
    fields = [
        _row("Member reference", "—", item.get("MEMBER_REFERENCE_NUMBER", "")),
        _row("Source name", "—", item.get("SOURCE_NAME", "")),
        _row("Enquiry date", "—", item.get("ENQUIRY_DATE", "")),
        _row("Error code", "—", item.get("ERRORCODE", "")),
        _row("Error message", "—", item.get("ERRORMSG", "")),
        _row("Application ID", "—", header.get("APPLICATION-ID", "")),
        _row("Multibureau cust ID", "—", header.get("CUST-ID", "")),
        _row("Tracking ID", "—", finished.get("TRACKING-ID", "")),
        _row("Acknowledgement ID", "—", base.get("ACKNOWLEDGEMENT-ID", "")),
        *_context_rows(initiate_request, callback),
    ]
    return _pack("mbEquifax", fields)


def extract_mb_highmark_highlights(initiate_request: dict[str, Any], callback: dict[str, Any]) -> dict[str, Any]:
    idn = _initiate_identity(initiate_request)
    iq = (
        callback.get("mbHighMark", {})
        .get("Body", {})
        .get("MultiBureauResponse", {})
        .get("RESPONSE", {})
        .get("FINISHED", {})
        .get("JSON-RESPONSE-OBJECT", {})
        .get("CHM_BASE_SROP_DOMAIN_LIST", [{}])[0]
        .get("CHM_BASE_SROP_DOMAIN_LIST1", {})
    )
    header = (
        callback.get("mbHighMark", {})
        .get("Body", {})
        .get("MultiBureauResponse", {})
        .get("RESPONSE", {})
        .get("HEADER", {})
    )
    finished = (
        callback.get("mbHighMark", {})
        .get("Body", {})
        .get("MultiBureauResponse", {})
        .get("RESPONSE", {})
        .get("FINISHED", {})
    )
    fields = [
        _row("Name", idn["fullName"], iq.get("NAME_IQ", ""), match=iq.get("NAME_IQ", "") == idn["fullName"]),
        _row("PAN", idn["pan"], iq.get("PAN_IQ", ""), match=iq.get("PAN_IQ", "") == idn["pan"]),
        _row("DOB", idn["dob"], iq.get("DOB_IQ", ""), match=iq.get("DOB_IQ", "") == idn["highmarkDob"]),
        _row("Gender", idn["gender"], iq.get("GENDER_IQ", "")),
        _row("Mobile", idn["mobile"], iq.get("PHONE_1_IQ", ""), match=iq.get("PHONE_1_IQ", "") == idn["mobile"]),
        _row("Email", idn["email"], iq.get("EMAIL_1_IQ", ""), match=iq.get("EMAIL_1_IQ", "") == idn["email"]),
        _row("Status", "—", iq.get("STATUS_IQ", "")),
        _row("Application ID", "—", header.get("APPLICATION-ID", "")),
        _row("Tracking ID", "—", finished.get("TRACKING-ID", "")),
        *_context_rows(initiate_request, callback),
    ]
    return _pack("mbHighMark", fields)


def extract_mb_mbeot_highlights(initiate_request: dict[str, Any], callback: dict[str, Any]) -> dict[str, Any]:
    idn = _initiate_identity(initiate_request)
    eot = (
        callback.get("mbMbEot", {})
        .get("Body", {})
        .get("MultiBureauEoTRequest", {})
    )
    header = eot.get("HEADER", {})
    fields = [
        _row("Status", "—", eot.get("STATUS", "")),
        _row("Sent to CIBIL", "—", eot.get("SENT-TO-CIBIL", "")),
        _row("Sent to Equifax", "—", eot.get("SENT-TO-EQUIFAX", "")),
        _row("Sent to Experian", "—", eot.get("SENT-TO-EXPERIAN", "")),
        _row("Sent to CHM", "—", eot.get("SENT-TO-CHM", "")),
        _row("Application ID", "—", header.get("APPLICATION-ID", "")),
        _row("Cust ID", idn["customerId"], header.get("CUST-ID", "")),
        _row("Acknowledgement ID", "—", eot.get("ACKNOWLEDGEMENT-ID", "")),
        *_context_rows(initiate_request, callback),
    ]
    return _pack("mbMbEot", fields)


def extract_perfios_highlights(initiate_request: dict[str, Any], callback: dict[str, Any]) -> dict[str, Any]:
    idn = _initiate_identity(initiate_request)
    body = callback.get("perfios", {})
    cust = body.get("CustomerInfo", {})
    summary = body.get("SummaryInfo", {})
    pd = initiate_request["applicant"]["productDetails"]["perfios"]
    fields = [
        _row("PAN", idn["pan"], cust.get("pan", ""), match=cust.get("pan", "") == idn["pan"]),
        _row("Name", idn["fullName"], cust.get("name", ""), match=cust.get("name", "") == idn["fullName"]),
        _row("Email", idn["email"], cust.get("email", ""), match=cust.get("email", "") == idn["email"]),
        _row("Mobile", idn["mobile"], cust.get("mobile", ""), match=cust.get("mobile", "") == idn["mobile"]),
        _row("Address", idn["perfiosAddress"], cust.get("address", ""), match=cust.get("address", "") == idn["perfiosAddress"]),
        _row("Employer", idn["employer"], body.get("AdditionalParameters", {}).get("employerName", ""), match=body.get("AdditionalParameters", {}).get("employerName", "") == idn["employer"]),
        _row("Grade", "—", summary.get("grade", "")),
        _row("Median salary", "—", summary.get("medianSalary", "")),
        _row("perfiosTransactionId", pd.get("perfiosTransactionId", ""), cust.get("perfiosTransactionId", ""), match=cust.get("perfiosTransactionId", "") == pd.get("perfiosTransactionId", "")),
        _row("customerTransactionId", "—", cust.get("customerTransactionId", "")),
        *_context_rows(initiate_request, callback),
    ]
    return _pack("perfios", fields)


def extract_posidex_highlights(initiate_request: dict[str, Any], callback: dict[str, Any]) -> dict[str, Any]:
    idn = _initiate_identity(initiate_request)
    rows = callback.get("posidex", {}).get("outputdata", [])
    row = rows[0] if rows else {}
    fields = [
        _row("First name (SOA_FNAME_C)", idn["fullName"], row.get("SOA_FNAME_C", ""), match=row.get("SOA_FNAME_C", "") == idn["fullName"]),
        _row("Last name", idn["lastName"], row.get("SOA_LNAME_C", ""), match=row.get("SOA_LNAME_C", "") == idn["lastName"]),
        _row("PAN (FILLER_35)", idn["pan"], row.get("FILLER_35", ""), match=row.get("FILLER_35", "") == idn["pan"]),
        _row("Match status", "—", row.get("SOA_STATUS_C", "")),
        _row("Match parameters", "—", row.get("SOA_MATCH_PARAMETER", "")),
        _row("SOA App ID", "—", row.get("SOA_APP_ID_C", "")),
        _row("Mobile", idn["mobile"], row.get("FILLER_40", ""), match=row.get("FILLER_40", "") == idn["mobile"]),
        _row("City", idn["city"], row.get("FILLER_2", ""), match=row.get("FILLER_2", "") == idn["city"]),
        _row("State", idn["state"], row.get("FILLER_22", ""), match=row.get("FILLER_22", "") == idn["state"]),
        _row("Pincode", idn["pinCode"], row.get("FILLER_29", ""), match=row.get("FILLER_29", "") == idn["pinCode"]),
        *_context_rows(initiate_request, callback),
    ]
    return _pack("posidex", fields)


def extract_hunter_highlights(initiate_request: dict[str, Any], callback: dict[str, Any]) -> dict[str, Any]:
    summary = (
        callback.get("hunter", {})
        .get("Body", {})
        .get("MatchResponse", {})
        .get("MatchResult", {})
        .get("ResultBlock", {})
        .get("MatchSummary", {})
    )
    fields = [
        _row("Total match score", "—", summary.get("TotalMatchScore", "")),
        _row("Matches", "—", summary.get("matches", "")),
        _row("reportType", "—", callback.get("reportType", "")),
        _row("statusCode", "—", callback.get("statusCode", "")),
        *_context_rows(initiate_request, callback),
    ]
    return _pack("hunter", fields)


def extract_summary_highlights(initiate_request: dict[str, Any], callback: dict[str, Any]) -> dict[str, Any]:
    summary = callback.get("applicant", {}).get("summary", {})
    fields = [
        _row(key, "—", value) for key, value in summary.items()
    ]
    fields.extend(_context_rows(initiate_request, callback))
    return _pack("summary", fields)


_EXTRACTORS = {
    "mbCibil": extract_mb_cibil_highlights,
    "mbEquifax": extract_mb_equifax_highlights,
    "mbHighMark": extract_mb_highmark_highlights,
    "mbMbEot": extract_mb_mbeot_highlights,
    "perfios": extract_perfios_highlights,
    "posidex": extract_posidex_highlights,
    "hunter": extract_hunter_highlights,
    "summary": extract_summary_highlights,
}


def extract_producer_highlights(
    initiate_request: dict[str, Any],
    report_type: str,
    callback: dict[str, Any],
) -> dict[str, Any]:
    extractor = _EXTRACTORS.get(report_type)
    if not extractor:
        raise ValueError(f"No highlights extractor for {report_type}")
    return extractor(initiate_request, callback)


def extract_all_producer_highlights(
    initiate_request: dict[str, Any],
    callbacks: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Build highlights for every callback received."""
    return {
        report_type: extract_producer_highlights(initiate_request, report_type, payload)
        for report_type, payload in callbacks.items()
        if report_type in _EXTRACTORS
    }


# Backward-compatible alias
def extract_cibil_highlights(
    initiate_request: dict[str, Any],
    mb_cibil_callback: dict[str, Any],
) -> dict[str, Any]:
    return extract_mb_cibil_highlights(initiate_request, mb_cibil_callback)

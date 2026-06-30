"""Parse EE initiate request JSON into internal profile + journey shapes."""

from __future__ import annotations

from typing import Any


def _mobile_fallback(pan: str) -> str:
    digits = "".join(c for c in pan if c.isdigit())
    tail = (digits + "5678901234")[:9]
    return "9" + tail


def profile_from_initiate(initiate: dict[str, Any]) -> dict[str, Any]:
    demog = initiate["applicant"]["customerDemog"]
    name = demog["name"][0]
    addr = demog["address"][0]
    first = name["fName"]
    middle = name.get("mName", "")
    last = name["lName"]
    emp = initiate["applicant"].get("employmentDetails", {})
    bank = initiate["applicant"]["bankingDetails"]

    return {
        "userIndex": "0",
        "userType": "applicant",
        "firstName": first,
        "middleName": middle,
        "lastName": last,
        "fullName": " ".join(p for p in (first, middle, last) if p),
        "pan": demog["ids"]["panNo"],
        "dob": demog["dob"],
        "gender": demog["gender"],
        "age": demog.get("age", ""),
        "email": demog["emailId1"],
        "mobile": demog.get("mobile") or _mobile_fallback(demog["ids"]["panNo"]),
        "addressType": addr.get("addresstype", "CURRENT"),
        "addressLine1": addr.get("address1", ""),
        "addressLine2": addr.get("address2", ""),
        "addressLine3": addr.get("address3", ""),
        "addressLine4": addr.get("address4", ""),
        "city": addr.get("city", ""),
        "state": addr.get("state", ""),
        "pinCode": addr.get("pinCode", ""),
        "employerName": emp.get("employerName", ""),
        "loanAmount": bank["loanDetails"]["loanAmount"],
        "customerId": bank["accountInfo"][0]["customerId"],
    }


def journey_from_initiate(initiate: dict[str, Any], orc_journey_id: str) -> dict[str, Any]:
    ctx = initiate["contextParameter"]
    return {
        "partnerJourneyID": ctx["partnerJourneyID"],
        "bankJourneyID": ctx["bankJourneyID"],
        "orcJourneyID": orc_journey_id,
        "partnerID": ctx["partnerID"],
        "channelID": ctx["channelID"],
        "productName": ctx["productName"],
        "productDetails": initiate["applicant"]["productDetails"],
    }


def co_applicant_count(initiate: dict[str, Any]) -> int:
    try:
        return int(initiate.get("coApplicants", {}).get("totalCoApplicants", "0"))
    except (TypeError, ValueError):
        return 0


def callback_order_for_initiate(initiate: dict[str, Any]) -> list[str]:
    """Producer callbacks to fire based on productDetails (summary always last)."""
    pd = initiate["applicant"]["productDetails"]
    order: list[str] = []
    if pd.get("multibureau"):
        order.extend(["mbCibil", "mbEquifax", "mbHighMark", "mbMbEot"])
    if pd.get("perfios"):
        order.append("perfios")
    if pd.get("posidex"):
        order.append("posidex")
    if pd.get("hunter"):
        order.append("hunter")
    order.append("summary")
    return order

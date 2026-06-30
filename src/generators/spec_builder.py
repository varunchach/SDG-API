"""Build initiateRequest and ackResponse in exact EE spec format."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from .json_utils import deep_copy, load_template, set_path


def _fill_applicant_block(
    req: dict[str, Any],
    prefix: str,
    profile: dict[str, Any],
    journey: dict[str, Any],
    *,
    form_date: str,
    include_employment: bool = True,
) -> None:
    """Fill applicant or coApplicantArray[n] paths under initiate request."""
    p = prefix
    set_path(req, f"{p}.customerSegment", "INDIVIDUAL")
    set_path(req, f"{p}.perfiosCustomerSegment", "RETAIL")
    set_path(req, f"{p}.mBueCustomerSegment", "Individual")
    set_path(req, f"{p}.customerDemog.name[0].fName", profile["firstName"])
    set_path(req, f"{p}.customerDemog.name[0].mName", profile.get("middleName", ""))
    set_path(req, f"{p}.customerDemog.name[0].lName", profile["lastName"])
    set_path(req, f"{p}.customerDemog.dob", profile["dob"])
    set_path(req, f"{p}.customerDemog.gender", profile["gender"])
    set_path(req, f"{p}.customerDemog.age", profile["age"])
    set_path(req, f"{p}.customerDemog.emailId1", profile["email"])
    if profile.get("mobile"):
        set_path(req, f"{p}.customerDemog.mobile", profile["mobile"])
    set_path(req, f"{p}.customerDemog.address[0].addresstype", profile["addressType"])
    set_path(req, f"{p}.customerDemog.address[0].address1", profile["addressLine1"])
    set_path(req, f"{p}.customerDemog.address[0].address2", profile["addressLine2"])
    set_path(req, f"{p}.customerDemog.address[0].address3", profile["addressLine3"])
    set_path(req, f"{p}.customerDemog.address[0].address4", profile["addressLine4"])
    set_path(req, f"{p}.customerDemog.address[0].city", profile["city"])
    set_path(req, f"{p}.customerDemog.address[0].pinCode", profile["pinCode"])
    set_path(req, f"{p}.customerDemog.address[0].state", profile["state"])
    set_path(req, f"{p}.customerDemog.ids.panNo", profile["pan"])

    if include_employment:
        set_path(req, f"{p}.employmentDetails.employerName", profile["employerName"])
        set_path(req, f"{p}.employmentDetails.companyCategory", "A")
        set_path(req, f"{p}.employmentDetails.companyNames", profile["employerName"][:20])

    set_path(req, f"{p}.bankingDetails.accountInfo[0].customerId", profile["customerId"])
    set_path(req, f"{p}.bankingDetails.accountInfo[0].formDate", form_date)
    set_path(req, f"{p}.bankingDetails.loanDetails.loanAmount", profile["loanAmount"])

    pd = journey["productDetails"]
    set_path(req, f"{p}.productDetails.multibureau.loanType", pd["multibureau"]["loanType"])
    set_path(req, f"{p}.productDetails.multibureau.responseFormat", pd["multibureau"]["responseFormat"])
    set_path(req, f"{p}.productDetails.perfios.txnId", pd["perfios"]["txnId"])
    set_path(req, f"{p}.productDetails.perfios.perfiosTransactionId", pd["perfios"]["perfiosTransactionId"])
    set_path(req, f"{p}.productDetails.posidex.sourceId", pd["posidex"]["sourceId"])
    set_path(req, f"{p}.productDetails.posidex.productId", pd["posidex"]["productId"])
    set_path(req, f"{p}.productDetails.posidex.priority", pd["posidex"]["priority"])
    set_path(req, f"{p}.productDetails.posidex.matchingProfile", pd["posidex"]["matchingProfile"])
    set_path(req, f"{p}.productDetails.posidex.branchId", pd["posidex"]["branchId"])
    set_path(req, f"{p}.productDetails.hunter.hunterProductPart1", pd["hunter"]["hunterProductPart1"])
    set_path(req, f"{p}.productDetails.hunter.hunterProductPart2", pd["hunter"]["hunterProductPart2"])


def build_initiate_request(
    profile: dict[str, Any],
    journey: dict[str, Any],
    *,
    co_profile: dict[str, Any] | None = None,
    app_id: str | None = None,
) -> dict[str, Any]:
    """Build initiate request from template; no orcJourneyID in contextParameter."""
    req = deep_copy(load_template("initiate-request"))

    set_path(req, "contextParameter.partnerJourneyID", journey["partnerJourneyID"])
    set_path(req, "contextParameter.bankJourneyID", journey["bankJourneyID"])
    set_path(req, "contextParameter.partnerID", journey["partnerID"])
    set_path(req, "contextParameter.channelID", journey["channelID"])
    set_path(req, "contextParameter.productName", journey["productName"])

    form_date = date.today().isoformat()
    _fill_applicant_block(req, "applicant", profile, journey, form_date=form_date)
    set_path(req, "applicant.bussinessDetails.appId", app_id or profile["customerId"])

    co = co_profile or profile
    set_path(req, "coApplicants.totalCoApplicants", "1")
    _fill_applicant_block(
        req,
        "coApplicants.coApplicantArray[0]",
        co,
        journey,
        form_date=form_date,
        include_employment=False,
    )
    set_path(req, "coApplicants.coApplicantArray[0].index", "1")

    set_path(req, "sourceApp.constitution", "")
    return req


def build_ack_response(
    journey: dict[str, Any],
    *,
    request_id: str | None = None,
    success: bool = True,
) -> dict[str, Any]:
    """Build sync ACK from template."""
    ack = deep_copy(load_template("ack-response"))
    set_path(ack, "data.orcJourneyID", journey["orcJourneyID"])
    set_path(ack, "data.bankJourneyID", journey["bankJourneyID"])
    set_path(ack, "data.partnerJourneyID", journey["partnerJourneyID"])
    if success:
        set_path(ack, "data.statusCode", "0")
        set_path(ack, "data.statusMessage", "Success")
    else:
        set_path(ack, "data.statusCode", "1")
        set_path(ack, "data.statusMessage", "Failure")
    set_path(ack, "messages.requestId", request_id or str(uuid.uuid4()))
    set_path(ack, "messages.status", "SUCCESS")
    set_path(ack, "messages.httpStatusCode", "200")
    return ack

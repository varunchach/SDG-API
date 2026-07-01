"""Overwrite every non-empty leaf in a spec template with synthetic journey data."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from faker import Faker

from .callback_formats import dob_to_cibil, dob_to_highmark, gender_cibil, gender_highmark
from .json_utils import deep_copy, get_path, set_path

_DATE_DDMMYYYY = re.compile(r"^\d{8}$")
_DATE_DD_MM_YYYY = re.compile(r"^\d{2}-\d{2}-\d{4}$")
_DATE_YYYY_MM_DD = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_DDMMYYYY_TIME = re.compile(r"^\d{8} \d{2}:\d{2}:\d{2}$")
_DATE_ISO_TIME = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d$")
_NUMERIC = re.compile(r"^-?\d+(\.\d+)?$")
_PAN = re.compile(r"^[A-Z]{5}\d{4}[A-Z]$")


@dataclass
class FillContext:
    producer: str
    profile: dict[str, Any]
    journey: dict[str, Any]
    system_ids: dict[str, Any]
    scenario: dict[str, Any]
    rng: random.Random
    faker: Faker
    posidex_row_profiles: dict[int, dict[str, Any]] | None = None


def _posidex_row_index(path: str) -> int | None:
    m = re.search(r"outputdata\[(\d+)\]", path)
    return int(m.group(1)) if m else None


def _posidex_row_profile(ctx: FillContext, row_index: int) -> dict[str, Any]:
    if row_index == 0:
        return ctx.profile
    cache = ctx.posidex_row_profiles
    if cache is not None and row_index in cache:
        return cache[row_index]
    from .indian_identity import generate_pan, pick_indian_name, pick_location

    row_rng = random.Random(abs(hash((ctx.journey.get("orcJourneyID", ""), "posidex", row_index))) % (2**31))
    gender = row_rng.choice(["M", "F"])
    first, middle, last = pick_indian_name(row_rng, gender)
    loc = pick_location(row_rng)
    pan = generate_pan(last, row_rng)
    profile = {
        "firstName": first,
        "middleName": middle,
        "lastName": last,
        "fullName": " ".join(p for p in (first, middle, last) if p),
        "pan": pan,
        "mobile": ctx.faker.numerify(text="%#########"),
        "city": loc["city"],
        "state": loc["state"],
        "pinCode": loc["pinCode"],
        "addressLine1": f"{row_rng.randint(1, 199)} {ctx.faker.street_name().upper()}",
        "addressLine2": "",
        "employerName": ctx.profile.get("employerName", "SYNTHETIC EMPLOYER"),
    }
    if cache is not None:
        cache[row_index] = profile
    return profile


def _active_profile(ctx: FillContext, path: str) -> dict[str, Any]:
    if ctx.producer == "posidex":
        idx = _posidex_row_index(path)
        if idx is not None and idx > 0:
            return _posidex_row_profile(ctx, idx)
    return ctx.profile


def make_fill_context(
    producer: str,
    profile: dict[str, Any],
    journey: dict[str, Any],
    system_ids: dict[str, Any],
    scenario: dict[str, Any],
) -> FillContext:
    seed = abs(hash((journey.get("orcJourneyID", ""), producer))) % (2**31)
    rng = random.Random(seed)
    faker = Faker("en_IN")
    faker.seed_instance(seed)
    return FillContext(
        producer=producer,
        profile=profile,
        journey=journey,
        system_ids=system_ids,
        scenario=scenario,
        rng=rng,
        faker=faker,
        posidex_row_profiles={} if producer == "posidex" else None,
    )


def _field_name(path: str) -> str:
    tail = path.split(".")[-1]
    return tail.split("[")[0]


def _path_rng(ctx: FillContext, path: str) -> random.Random:
    seed = abs(hash((ctx.journey.get("orcJourneyID", ""), path))) % (2**31)
    return random.Random(seed)


def _today(ctx: FillContext) -> datetime:
    base = datetime.now()
    offset = ctx.rng.randint(-30, 0)
    return base + timedelta(days=offset)


def _format_date_like(sample: str, ctx: FillContext, path: str) -> str:
    dt = _today(ctx)
    if _DATE_DDMMYYYY.match(sample):
        return dt.strftime("%d%m%Y")
    if _DATE_DD_MM_YYYY.match(sample):
        return dt.strftime("%d-%m-%Y")
    if _DATE_YYYY_MM_DD.match(sample):
        return dt.strftime("%Y-%m-%d")
    if _DATE_DDMMYYYY_TIME.match(sample):
        return dt.strftime("%d%m%Y %H:%M:%S")
    if _DATE_ISO_TIME.match(sample):
        return dt.strftime("%Y-%m-%d %H:%M:%S.0")
    if " " in sample and "-" in sample:
        return dt.strftime("%Y-%m-%d %H:%M:%S.0")
    return dt.strftime("%Y-%m-%d")


def _amount_like(sample: str, ctx: FillContext, path: str) -> str:
    """Generate monetary value within decimal(12,2) — max 10 digits before decimal."""
    rng = _path_rng(ctx, path)
    if "." in sample:
        frac_len = len(sample.split(".", 1)[1])
        whole_max = min(10, max(1, len(sample.split(".", 1)[0])))
        val = rng.uniform(1, 10**whole_max - 1)
        return f"{val:.{frac_len}f}"
    val = rng.randint(1, 999_999_999)
    return str(val)


def _numeric_like(sample: str, ctx: FillContext, path: str) -> str:
    rng = _path_rng(ctx, path)
    if "." in sample:
        whole, frac = sample.split(".", 1)
        val = rng.uniform(10 ** (len(whole) - 1), 10 ** len(whole) - 1)
        return f"{val:.{len(frac)}f}"
    length = len(sample.lstrip("-"))
    if sample.startswith("-"):
        return "-" + "".join(str(rng.randint(1, 9) if i == 0 else rng.randint(0, 9)) for i in range(length))
    return "".join(str(rng.randint(1, 9) if i == 0 else rng.randint(0, 9)) for i in range(length))


def _masked_account(sample: str, ctx: FillContext, path: str) -> str:
    rng = _path_rng(ctx, path)
    out = []
    for ch in sample:
        if ch == "X":
            out.append(str(rng.randint(0, 9)))
        else:
            out.append(ch)
    return "".join(out)


def _mb(ctx: FillContext) -> dict[str, Any]:
    return ctx.system_ids["multibureau"]


def _bureau_tracking(ctx: FillContext) -> str:
    key = {
        "mbCibil": "mbCibil",
        "mbEquifax": "mbEquifax",
        "mbHighMark": "mbHighMark",
    }.get(ctx.producer, "mbCibil")
    return _mb(ctx)["trackingIds"][key]


def _resolve_envelope(path: str, sample: str, ctx: FillContext) -> str | None:
    j = ctx.journey
    mapping = {
        "contextParameter.partnerJourneyID": j["partnerJourneyID"],
        "contextParameter.bankJourneyID": j["bankJourneyID"],
        "contextParameter.orcJourneyID": j["orcJourneyID"],
        "contextParameter.partnerID": j["partnerID"],
        "contextParameter.channelID": j["channelID"],
        "contextParameter.productName": j["productName"],
        "statusCode": "0",
        "statusMsg": "Success",
        "reportType": ctx.producer,
    }
    if path in mapping:
        return str(mapping[path])
    if path == "userType":
        return "applicant"
    if path == "userIndex":
        return "0"
    return None


def _resolve_mb_header(path: str, sample: str, ctx: FillContext) -> str | None:
    mb = _mb(ctx)
    if path.endswith("APPLICATION-ID"):
        return mb["applicationId"]
    if path.endswith("CUST-ID"):
        return mb["custId"]
    if path.endswith("ACKNOWLEDGEMENT-ID"):
        return mb["acknowledgementId"]
    if path.endswith("TRACKING-ID"):
        return _bureau_tracking(ctx)
    if path.endswith("RESPONSE-TYPE"):
        return "RESPONSE"
    if path.endswith("REQUEST-RECEIVED-TIME"):
        return _format_date_like(sample, ctx, path)
    return None


def _resolve_structural(field: str, path: str, sample: str, ctx: FillContext) -> str | None:
    """Bureau/system codes and institution names — not applicant identity."""
    if field in {"SOURCE_NAME", "SOA_SOURCE_NAME", "SOURCE-SYSTEM"}:
        return sample
    if field == "MEMBER_NAME":
        if "BANK" in sample.upper() or "LTD" in sample.upper():
            return sample
        return "NATIONAL BANK LTD"
    if field in {
        "ERRORCODE",
        "OUTPUT_WRITE_FLAG",
        "RuleID",
        "isGlobal",
        "ruleCount",
        "totalRuleCount",
    }:
        if _NUMERIC.match(sample):
            return _numeric_like(sample, ctx, path)
        return sample
    if field.startswith("ENRICHED_THROUGH_"):
        return sample
    if field in {
        "SOURCE-SYSTEM",
        "STATUS",
        "BUREAU",
        "PRODUCT",
        "PREPARED_FOR",
        "MATCHED_TYPE",
        "OWNERSHIP_TYPE",
        "OWNERSHIP_IND",
        "ID_TYPE",
        "CREDT_INQ_PURPS_TYP_IQ",
        "CREDIT_INQUIRY_STAGE_IQ",
        "ACCT_TYPE",
        "ACCOUNT_STATUS",
        "applicantType",
        "productType",
        "sourceSystem",
        "sourceOfData",
        "SOA_SAS_UPDATE_STATUS",
        "SOA_BORROWER_F",
        "SOA_CUST_TYPE_C",
        "SOA_SOURCE_C",
        "SOA_MATCH_PARAMETER",
        "FILLER_20",
        "FILLER_21",
        "FILLER_31",
        "FILLER_32",
        "FILLER_33",
    }:
        return sample
    return None


def _resolve_identity(field: str, path: str, sample: str, ctx: FillContext) -> str | None:
    p = _active_profile(ctx, path)
    if field == "CONSUMER_NAME_FIELD1":
        return p["fullName"]
    if field == "NAME_IQ":
        return p["fullName"]
    if field == "NAME" and "CHM_BASE_SROP_DOMAIN_LIST1" in path:
        return p["fullName"]
    if field == "SOA_FNAME_C":
        return p["fullName"]
    if field in {"SOA_LNAME_C"}:
        return p["lastName"]
    if field == "SOA_MNAME_C":
        middle = p.get("middleName", "")
        if middle:
            return middle
        if sample:
            return ctx.faker.first_name().upper()
        return ""
    if field == "CUSTOMER_NAME":
        return p["fullName"]
    if field in {"ID_NUMBER", "PAN_IQ", "FILLER_35"}:
        return p["pan"]
    if field == "pan":
        return p["pan"]
    if field in {"DATE_OF_BIRTH"}:
        return dob_to_cibil(p["dob"])
    if field in {"DOB_IQ"}:
        return dob_to_highmark(p["dob"])
    if field in {"GENDER"}:
        return gender_cibil(p["gender"])
    if field in {"GENDER_IQ"}:
        return gender_highmark(p["gender"])
    if field in {"EMAIL_1_IQ"} or field == "email":
        return p["email"]
    if field in {"PHONE_1_IQ", "mobile", "landline", "FILLER_40"}:
        return p["mobile"]
    if field in {"ADDRESS_LINE_1", "ADDRESS_1_IQ", "FILLER_10", "FILLER_42"}:
        return p["addressLine1"]
    if field in {"ADDRESS_LINE_2", "ADDRESS_2_IQ", "FILLER_11"}:
        return p["addressLine2"]
    if field in {"PINCODE", "FILLER_12", "FILLER_29", "FILLER_45"}:
        return p["pinCode"]
    if field in {"STATE", "FILLER_22", "FILLER_28"}:
        return p["state"]
    if field in {"FILLER_2", "FILLER_27", "FILLER_43", "city"}:
        return p["city"]
    if field in {"name", "pan"}:
        return p[field]
    if field == "address":
        return f"{p['addressLine1']}, {p['city']}, {p['state']} {p['pinCode']}"
    if field == "employerName":
        return p["employerName"]
    return None


def _resolve_scenario(field: str, path: str, sample: str, ctx: FillContext) -> str | None:
    if field == "SCORE":
        return ctx.scenario.get("mbCibil", {}).get("score", "742")
    if field == "SUBJECT_RETURN_CODE":
        return ctx.scenario.get("mbCibil", {}).get("subjectReturnCode", "FOUND")
    if field == "ERRORMSG":
        msg = ctx.scenario.get("mbEquifax", {}).get("errorMsg", "SUCCESS")
        return msg if msg else "SUCCESS"
    if field == "STATUS_IQ":
        return ctx.scenario.get("mbHighMark", {}).get("statusIq", "SUCCESS")
    if field == "SOA_STATUS_C":
        idx = _posidex_row_index(path)
        if idx is not None and idx > 0:
            return sample if sample in {"Match", "No Match"} else "Match"
        return ctx.scenario.get("posidex", {}).get("soaStatus", "No Match")
    if field == "matches":
        return ctx.scenario.get("hunter", {}).get("matches", ctx.system_ids["hunter"]["matches"])
    if field == "TotalMatchScore":
        return ctx.scenario.get("hunter", {}).get(
            "totalMatchScore", ctx.system_ids["hunter"]["totalMatchScore"]
        )
    if field == "grade":
        return ctx.scenario.get("perfios", {}).get("grade", "AAA")
    if field in {"medianSalary", "totalSalary", "avgSalary"}:
        return ctx.scenario.get("perfios", {}).get("medianSalary", "40750")
    return None


def _resolve_system_ids(field: str, path: str, sample: str, ctx: FillContext) -> str | None:
    mb = _mb(ctx)
    if field == "MEMBER_REFERENCE_NUMBER":
        return mb["custId"]
    if field == "SOA_APP_ID_C":
        return ctx.system_ids["posidex"]["soaAppId"]
    if field == "SOA_MATCH_APPID_C":
        ids = ctx.system_ids["posidex"].get("soaMatchAppIds", [])
        return ids[0] if ids else _numeric_like(sample, ctx, path)
    if field == "perfiosTransactionId":
        return ctx.journey["productDetails"]["perfios"]["perfiosTransactionId"]
    if field == "customerTransactionId":
        return ctx.system_ids["perfios"]["customerTransactionId"]
    if field == "LOS_APP_ID_IQ":
        return mb["applicationId"]
    if field == "MBR_ID_IQ":
        return mb["custId"]
    if field == "SRNO":
        return _numeric_like(sample, ctx, path)
    if field == "SOA_FILE_NAME_C":
        rng = _path_rng(ctx, path)
        return f"SCFCI{rng.randint(10**2, 10**3)}A{_numeric_like('0' * 40, ctx, path)}"
    if field == "SOA_MATCH_PARAMETER" or field == "FILLER_31":
        return "NAME,PAN"
    if field == "SOA_DEDUPE_DATE" or field == "SOA_SAS_UPDATE_DATE":
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.0")
    if field == "FILLER_3":
        return ctx.profile["employerName"]
    if field == "FILLER_20" or field == "SOA_BORROWER_F":
        return "A"
    if field == "FILLER_21":
        return "0"
    if field == "FILLER_32" or field == "SOA_USER_ID":
        return "SYSTEM"
    if field == "FILLER_33":
        return "Normal"
    if field == "SOA_SAS_UPDATE_STATUS":
        return "Y"
    if field == "SOA_SOURCE_C":
        return "FINNONE"
    if field == "SOA_CUST_TYPE_C":
        return "G"
    if ctx.producer == "mbMbEot":
        eot = mb["eot"]
        if field == "STATUS":
            return "END-OF-TXN"
        if field == "SENT-TO-CIBIL":
            return eot["sentToCibil"]
        if field == "SENT-TO-EQUIFAX":
            return eot["sentToEquifax"]
        if field == "SENT-TO-EXPERIAN":
            return eot["sentToExperian"]
        if field == "SENT-TO-CHM":
            return eot["sentToChm"]
    return None


def _resolve_bureau_domain(field: str, path: str, sample: str, ctx: FillContext) -> str | None:
    if field == "PREPARED_FOR_ID":
        return f"PRB{_numeric_like('0000000', ctx, path)}"
    if field == "REPORT_ID":
        dt = _today(ctx).strftime("%y%m%d")
        return f"SDG{dt}CR{_numeric_like('0000000', ctx, path)}"
    if field == "BATCH_ID":
        return _numeric_like(sample, ctx, path)
    if field == "BRANCH_IQ":
        return ctx.profile.get("city", ctx.faker.city()).upper()
    if field == "SCORE_FACTORS":
        rng = _path_rng(ctx, path)
        parts = [f"SF{rng.randint(10, 99)}" for _ in range(3)]
        return "|".join(parts) + "||"
    if field == "referenceNumber":
        return "BS" + _numeric_like(sample[2:], ctx, path)
    if field == "bank":
        return f"{ctx.faker.company().upper()} BANK LTD"
    if field == "instId":
        return _numeric_like(sample, ctx, path)
    if field == "landline":
        return ctx.faker.numerify(text="0##-#######")
    if field == "durationInMonths":
        return str(ctx.rng.randint(3, 12))
    if field == "sourceOfData":
        return sample
    if field in {
        "SOURCE-SYSTEM",
        "STATUS",
        "BUREAU",
        "PRODUCT",
        "PREPARED_FOR",
        "MATCHED_TYPE",
        "OWNERSHIP_TYPE",
        "OWNERSHIP_IND",
        "ID_TYPE",
        "CREDT_INQ_PURPS_TYP_IQ",
        "CREDIT_INQUIRY_STAGE_IQ",
        "ACCT_TYPE",
        "ACCOUNT_STATUS",
        "applicantType",
        "productType",
        "sourceSystem",
    }:
        return sample
    return None


def resolve_value(path: str, sample: str, ctx: FillContext) -> str:
    """Return synthetic value for a non-empty template leaf."""
    field = _field_name(path)

    for resolver in (
        _resolve_envelope,
        _resolve_mb_header,
        lambda p, s, c: _resolve_structural(field, p, s, c),
        lambda p, s, c: _resolve_scenario(field, p, s, c),
        lambda p, s, c: _resolve_system_ids(field, p, s, c),
        lambda p, s, c: _resolve_bureau_domain(field, p, s, c),
        lambda p, s, c: _resolve_identity(field, p, s, c),
    ):
        val = resolver(path, sample, ctx)
        if val is not None:
            return val

    if "DATE" in field or field.endswith("_DT") or field.endswith("_DATE"):
        return _format_date_like(sample, ctx, path)

    if field in {"accountNo", "accNo"} or "X" in sample:
        return _masked_account(sample, ctx, path)

    if any(token in field for token in ("AMT", "AMOUNT", "DISBURSED", "INSTALLMENT", "SALARY", "EXPOSURE")):
        if "." in sample or _NUMERIC.match(sample):
            return _amount_like(sample, ctx, path)

    if _PAN.match(sample):
        return ctx.faker.bothify(text="?????####?").upper()

    if _NUMERIC.match(sample):
        return _numeric_like(sample, ctx, path)

    if "Success/Failed/Late/Not Opted" in sample and ".summary." in path:
        return sample.split("/")[0]

    words = sample.split()
    if len(words) <= 6:
        return ctx.faker.name().upper() if sample.isupper() else ctx.faker.company()

    return ctx.faker.text(max_nb_chars=min(len(sample), 120)).upper() if sample.isupper() else ctx.faker.text(
        max_nb_chars=min(len(sample), 120)
    )


def collect_all_nonempty_paths(
    template_node: Any,
    path: str = "",
    out: list[tuple[str, str]] | None = None,
) -> list[tuple[str, str]]:
    """Every non-empty leaf in the full spec template tree (all list indices)."""
    rows: list[tuple[str, str]] = [] if out is None else out
    if isinstance(template_node, dict):
        for key, val in template_node.items():
            child = f"{path}.{key}" if path else key
            collect_all_nonempty_paths(val, child, rows)
    elif isinstance(template_node, list):
        for i, item in enumerate(template_node):
            collect_all_nonempty_paths(item, f"{path}[{i}]", rows)
    elif template_node not in (None, ""):
        rows.append((path, str(template_node)))
    return rows


def ensure_template_structure(template_node: Any, generated_node: Any) -> None:
    """Expand generated lists and dict keys to match the spec template shape."""
    if isinstance(template_node, dict) and isinstance(generated_node, dict):
        for key, t_val in template_node.items():
            if key not in generated_node:
                generated_node[key] = deep_copy(t_val)
            else:
                ensure_template_structure(t_val, generated_node[key])
    elif isinstance(template_node, list) and isinstance(generated_node, list):
        if not template_node:
            return
        prototype = template_node[0]
        while len(generated_node) < len(template_node):
            generated_node.append(deep_copy(prototype))
        for i, g_item in enumerate(generated_node):
            ensure_template_structure(template_node[min(i, len(template_node) - 1)], g_item)


def collect_nonempty_paths_aligned(
    template_node: Any,
    generated_node: Any,
    path: str,
    out: list[tuple[str, str]],
) -> None:
    """Pair template non-empty leaves with paths present in generated JSON."""
    if isinstance(template_node, dict) and isinstance(generated_node, dict):
        for key, t_val in template_node.items():
            if key not in generated_node:
                continue
            child = f"{path}.{key}" if path else key
            collect_nonempty_paths_aligned(t_val, generated_node[key], child, out)
        return

    if isinstance(template_node, list) and isinstance(generated_node, list):
        if not template_node:
            return
        for i, g_item in enumerate(generated_node):
            t_item = template_node[min(i, len(template_node) - 1)]
            collect_nonempty_paths_aligned(t_item, g_item, f"{path}[{i}]", out)
        return

    if template_node not in (None, ""):
        out.append((path, str(template_node)))


def apply_nonempty_fills(
    generated: dict[str, Any],
    template: dict[str, Any],
    ctx: FillContext,
) -> None:
    """Overwrite every non-empty template leaf in generated with synthetic data."""
    ensure_template_structure(template, generated)
    for path, sample in collect_all_nonempty_paths(template):
        try:
            set_path(generated, path, resolve_value(path, sample, ctx))
        except (KeyError, IndexError, TypeError, ValueError):
            continue

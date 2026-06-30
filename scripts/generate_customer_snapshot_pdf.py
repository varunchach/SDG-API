#!/usr/bin/env python3
"""Generate customer-facing POC snapshot PDF with clickable URLs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.generators.spec_templates import load_spec_initiate_request

OUT = ROOT / "docs" / "customer" / "HDFC_Eligibility_Engine_POC_Snapshot.pdf"
CURL_SH = ROOT / "docs" / "customer" / "generate-callbacks-curl.sh"

BASE = "https://hdfc-eligibility-live-default.apps.ocp.kxxfq.sandbox565.opentlc.com"
POST_URL = f"{BASE}/api/eligibility/generate-callbacks?scenario=clean-approval"

LINK = (0, 102, 204)
BODY = (33, 33, 33)
MUTED = (80, 80, 80)


class SnapshotPDF(FPDF):
    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


def _reset_x(pdf: FPDF) -> None:
    pdf.set_x(pdf.l_margin)


def _heading(pdf: FPDF, text: str) -> None:
    pdf.ln(3)
    _reset_x(pdf)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*BODY)
    pdf.multi_cell(0, 7, text)
    pdf.ln(1)


def _body(pdf: FPDF, text: str) -> None:
    _reset_x(pdf)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*BODY)
    pdf.multi_cell(0, 5, text)
    pdf.ln(1)


def _bullet(pdf: FPDF, text: str) -> None:
    _reset_x(pdf)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*BODY)
    pdf.multi_cell(0, 5, f"  -  {text}")


def _link_block(pdf: FPDF, label: str, url: str) -> None:
    _reset_x(pdf)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*BODY)
    pdf.cell(0, 6, f"{label}:", new_x="LMARGIN", new_y="NEXT")
    _reset_x(pdf)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*LINK)
    pdf.multi_cell(0, 5, url, link=url)
    pdf.ln(1)


def _code_lines(pdf: FPDF, lines: list[str], *, size: int = 7) -> None:
    pdf.set_font("Courier", "", size)
    pdf.set_text_color(40, 40, 40)
    pdf.set_fill_color(245, 245, 245)
    for line in lines:
        _reset_x(pdf)
        pdf.multi_cell(0, 3.8, line, fill=True)
    pdf.ln(2)


def _build_direct_curl() -> str:
    body = json.dumps(load_spec_initiate_request(), separators=(",", ":"))
    return (
        f'curl -X POST "{POST_URL}" \\\n'
        f'  -H "Content-Type: application/json" \\\n'
        f"  -d '{body}'"
    )


def _identity_table(pdf: FPDF) -> None:
    _reset_x(pdf)
    col_w = (52, 62, 62)
    headers = ("Field", "Applicant", "Co-applicant")
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(230, 236, 245)
    pdf.set_text_color(*BODY)
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 8, h, border=1, fill=True, align="C")
    pdf.ln()

    rows = [
        ("Name", "PRANAV SANTOSH", "PRANAV SANTOSH"),
        ("DOB", "1982-09-26", "1982-09-26"),
        ("PAN", "QAZPC8801X", "QAZPC8801X"),
        ("Email", "abcdefg@gmail.com", "abcdefg@gmail.com"),
        ("Gender / Age", "M / 25", "M / 25"),
    ]
    pdf.set_font("Helvetica", "", 9)
    fill = False
    for row in rows:
        _reset_x(pdf)
        if fill:
            pdf.set_fill_color(248, 248, 248)
        for i, val in enumerate(row):
            pdf.cell(col_w[i], 7, val, border=1, fill=fill)
        pdf.ln()
        fill = not fill
    pdf.ln(3)


def build_pdf() -> Path:
    direct_curl = _build_direct_curl()
    CURL_SH.write_text("#!/bin/bash\n" + direct_curl + "\n", encoding="utf-8")
    CURL_SH.chmod(0o755)

    pdf = SnapshotPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    _reset_x(pdf)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*BODY)
    pdf.cell(0, 10, "HDFC Eligibility Engine", new_x="LMARGIN", new_y="NEXT", align="C")

    _reset_x(pdf)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, "Mock Producer API (POC) - Customer Snapshot", new_x="LMARGIN", new_y="NEXT", align="C")

    _reset_x(pdf)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(*MUTED)
    pdf.cell(0, 6, "Synthetic test data only | March 2026", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)

    _heading(pdf, "1. Overview")
    _body(
        pdf,
        "Mock Producer API simulating the HDFC Eligibility Engine loan journey. "
        "Not connected to real bureau, Perfios, Posidex, or Hunter systems.",
    )
    _body(pdf, "Flow: Partner POSTs EE initiate JSON -> ACK + producer callbacks (mock).")
    _bullet(
        pdf,
        "Callbacks: mbCibil, mbEquifax, mbHighMark, mbMbEot, perfios, posidex, hunter, summary",
    )

    _heading(pdf, "2. Public Access")
    _body(pdf, "No OpenShift login required. Use these URLs directly (clickable in PDF):")
    _link_block(pdf, "Base URL", BASE)
    _link_block(pdf, "Web UI", f"{BASE}/")
    _link_block(pdf, "Swagger API docs", f"{BASE}/docs")
    _link_block(pdf, "Health check", f"{BASE}/api/health")
    _link_block(pdf, "Sample initiate JSON", f"{BASE}/api/samples/ee-initiate-request")
    _link_block(pdf, "Main API (generate callbacks)", POST_URL)

    _heading(pdf, "3. Sample Identity")
    _body(pdf, "From EE- initiate request V1.0.txt (spec sample - not real customer data):")
    _identity_table(pdf)
    _body(
        pdf,
        "Journey IDs: partnerJourneyID 345005711293 | bankJourneyID 45562927123 | "
        "partnerID FYNDNA | channelID CHANNEL_FYNDNA_HL1 | productName FYNDNA_HL1",
    )

    _heading(pdf, "4. Request Format")
    _bullet(pdf, "POST the full EE initiate JSON as the request body (see Appendix A)")
    _bullet(pdf, "Body matches EE- initiate request V1.0.txt exactly")
    _bullet(pdf, "productDetails is under applicant (not at root)")
    _bullet(pdf, "Do NOT include orcJourneyID in the request")
    _bullet(
        pdf,
        "Optional query: ?scenario=clean-approval "
        "(also: thin-file, fraud-hit, posidex-match, bureau-not-found)",
    )

    _heading(pdf, "5. Quick Tests")
    _body(pdf, "Health check:")
    _code_lines(pdf, [f"curl {BASE}/api/health"])

    _body(pdf, "Generate callbacks (direct POST with full EE initiate JSON):")
    _code_lines(
        pdf,
        [
            f'curl -X POST "{POST_URL}" \\',
            '  -H "Content-Type: application/json" \\',
            "  -d '<EE initiate JSON - full command in Appendix A>'",
        ],
    )
    _body(
        pdf,
        "Expected: ACK + 8 callbacks; PAN, name, and DOB match the initiate request. "
        "Complete copy-paste curl is in Appendix A.",
    )

    _heading(pdf, "6. Notes")
    _bullet(pdf, "POC environment - public URL, no API authentication (not for production)")
    _bullet(pdf, "Input spec: EE- initiate request V1.0.txt")
    _bullet(pdf, "Output specs: producer callback sample files in EE spec pack")
    _bullet(pdf, f"Async mode: POST {BASE}/api/journey/initiate (~3s between callbacks)")

    pdf.add_page()
    _heading(pdf, "Appendix A - Complete generate-callbacks curl")
    _body(
        pdf,
        "Copy and run this command. The -d body is the full EE initiate JSON from the spec sample.",
    )
    body = json.dumps(load_spec_initiate_request(), separators=(",", ":"))
    _code_lines(
        pdf,
        [
            f'curl -X POST "{POST_URL}" \\',
            '  -H "Content-Type: application/json" \\',
            f"  -d '{body}'",
        ],
        size=5,
    )

    _heading(pdf, "Appendix B - Request body JSON (formatted)")
    _body(pdf, "Same JSON used in the -d argument above (EE- initiate request V1.0.txt):")
    pretty = json.dumps(load_spec_initiate_request(), indent=2)
    _code_lines(pdf, pretty.splitlines(), size=6)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(OUT)
    return OUT


def main() -> None:
    path = build_pdf()
    print(f"Wrote {path}")
    print(f"Wrote {CURL_SH}")


if __name__ == "__main__":
    main()

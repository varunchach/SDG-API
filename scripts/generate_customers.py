#!/usr/bin/env python3
"""Generate N synthetic Indian customer records for producer system simulation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.generators.customer import generate_customer_batch  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic customer records")
    parser.add_argument("-n", "--count", type=int, default=100, help="Number of records")
    parser.add_argument("-s", "--seed", type=int, default=42, help="Random seed")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=ROOT / "data" / "generated",
        help="Output directory",
    )
    args = parser.parse_args()

    records = generate_customer_batch(args.count, seed=args.seed)

    out_dir = args.output
    out_dir.mkdir(parents=True, exist_ok=True)

    batch_path = out_dir / "customers-batch.json"
    batch_path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")

    per_customer_dir = out_dir / "customers"
    per_customer_dir.mkdir(exist_ok=True)
    for rec in records:
        path = per_customer_dir / f"{rec['recordId']}.json"
        path.write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")

    # Flat index for quick lookup
    index = [
        {
            "recordId": r["recordId"],
            "pan": r["initiateRequest"]["applicant"]["customerDemog"]["ids"]["panNo"],
            "fullName": r["profile"]["fullName"],
            "city": r["profile"]["city"],
            "orcJourneyID": r["ackResponse"]["data"]["orcJourneyID"],
            "scenario": r["scenario"],
        }
        for r in records
    ]
    (out_dir / "customers-index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"Generated {len(records)} customer records")
    print(f"  Batch:   {batch_path}")
    print(f"  Per-ID:  {per_customer_dir}/")
    print(f"  Index:   {out_dir / 'customers-index.json'}")
    pan = records[0]["initiateRequest"]["applicant"]["customerDemog"]["ids"]["panNo"]
    print(f"  Sample PAN: {pan} ({records[0]['profile']['fullName']})")
    print(f"  Scenarios: {sorted({r['scenario'] for r in records})}")
    print(
        "  Uniqueness: pan, mobile, email, customerId, "
        "partnerJourneyID, bankJourneyID, orcJourneyID — all distinct"
    )


if __name__ == "__main__":
    main()

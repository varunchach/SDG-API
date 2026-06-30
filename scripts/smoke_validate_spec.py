#!/usr/bin/env python3
"""
Smoke-test generated payloads against EE spec templates (data/templates/).

Usage:
  .venv/bin/python scripts/smoke_validate_spec.py
  .venv/bin/python scripts/smoke_validate_spec.py --count 20 --seed 99
  .venv/bin/python scripts/smoke_validate_spec.py --live-build
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.generators.customer import generate_customer_batch
from src.generators.live_record import generate_initiate_from_identity
from src.generators.txt_fill_audit import validate_callbacks_filled
from src.generators.uniqueness import IdentityRegistry
from src.generators.validate import validate_record
from src.producer.sync_service import run_sync_producers


def _check_batch_uniqueness(records: list[dict]) -> list[str]:
    registry = IdentityRegistry()
    return registry.audit_records(records)


def smoke_batch(count: int, seed: int) -> tuple[int, list[str]]:
    records = generate_customer_batch(count, seed=seed)
    errors: list[str] = []
    errors.extend(_check_batch_uniqueness(records))
    for rec in records:
        rec_errors = validate_record(rec)
        if rec_errors:
            errors.append(f"{rec['recordId']}: {rec_errors[0]}")
            if len(rec_errors) > 1:
                errors.append(f"  (+{len(rec_errors) - 1} more)")
        fill_errors = validate_callbacks_filled(rec["callbacks"], rec.get("profile"))
        for fe in fill_errors:
            errors.append(f"{rec['recordId']} txt-fill: {fe}")
    return len(records), errors


def smoke_live_build() -> tuple[int, list[str]]:
    errors: list[str] = []
    built = generate_initiate_from_identity(
        full_name="SMOKE TEST USER",
        dob="1985-06-15",
        pan_no="SMOKA1234B",
        scenario="clean-approval",
    )
    sync = run_sync_producers(built["initiateRequest"], built["scenario"], validate=True)
    if sync.get("validationErrors"):
        errors.extend(sync["validationErrors"])
    return 1, errors


def smoke_sync_api_sample() -> tuple[int, list[str]]:
    records = generate_customer_batch(3, seed=7)
    errors: list[str] = []
    for rec in records:
        sync = run_sync_producers(rec["initiateRequest"], rec["scenario"], validate=True)
        if sync.get("validationErrors"):
            errors.append(f"sync {rec['recordId']}: {sync['validationErrors'][0]}")
    return 3, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke validate generated data vs EE spec templates")
    parser.add_argument("--count", type=int, default=10, help="Batch records to generate")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--live-build", action="store_true", help="Also test live identity build + sync API path")
    parser.add_argument("--json", action="store_true", help="Print JSON summary")
    args = parser.parse_args()

    all_errors: list[str] = []
    total = 0

    print(f"=== Batch smoke ({args.count} records, seed={args.seed}) ===")
    n, errs = smoke_batch(args.count, args.seed)
    total += n
    all_errors.extend(errs)
    print(f"  records: {n}, errors: {len(errs)}")

    print("=== Sync producer API path (3 records) ===")
    n2, errs2 = smoke_sync_api_sample()
    total += n2
    all_errors.extend(errs2)
    print(f"  records: {n2}, errors: {len(errs2)}")

    if args.live_build:
        print("=== Live identity build + sync ===")
        n3, errs3 = smoke_live_build()
        total += n3
        all_errors.extend(errs3)
        print(f"  records: {n3}, errors: {len(errs3)}")

    passed = len(all_errors) == 0
    summary = {
        "passed": passed,
        "recordsChecked": total,
        "errorCount": len(all_errors),
        "errors": all_errors[:20],
    }

    if args.json:
        print(json.dumps(summary, indent=2))
    elif all_errors:
        print("\nFailures:")
        for e in all_errors[:15]:
            print(f"  - {e}")
        if len(all_errors) > 15:
            print(f"  ... and {len(all_errors) - 15} more")
    else:
        print("\nAll smoke checks passed.")

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

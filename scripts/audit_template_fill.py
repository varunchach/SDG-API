#!/usr/bin/env python3
"""Audit callback fill rate vs EE spec .txt sample files."""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from faker import Faker

from src.generators.customer import generate_customer_record
from src.generators.txt_fill_audit import PRODUCERS, audit_callbacks, validate_callbacks_filled
from src.generators.uniqueness import IdentityRegistry


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit callback fills vs spec .txt templates")
    parser.add_argument("--scenario", default="clean-approval")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--strict", action="store_true", help="Exit 1 if any empty or blocklisted values")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    faker = Faker("en_IN")
    faker.seed_instance(args.seed)
    record = generate_customer_record(
        rng, faker, IdentityRegistry(), record_id=1, scenario=args.scenario
    )
    callbacks = record["callbacks"]
    report = audit_callbacks(callbacks)

    print(f"Spec .txt fill audit (scenario={args.scenario}, seed={args.seed})\n")
    print(f"{'Producer':<12} {'Nonempty':>8} {'Filled%':>8} {'Empty%':>7} {'Miss%':>7} {'Static':>7}")
    print("-" * 58)

    for name in PRODUCERS:
        stats = report[name]
        print(
            f"{name:<12} {stats['total']:>8} {stats['generated_pct']:>7}% "
            f"{stats['empty_pct']:>6}% {stats['missing_pct']:>6}% {stats['static']:>7}"
        )

    errors = validate_callbacks_filled(callbacks, record.get("profile"))
    if errors:
        print("\nIssues:")
        for err in errors:
            print(f"  - {err}")
        if args.strict:
            return 1
    else:
        print("\nAll non-empty spec .txt fields have generated values (no blocklisted sample literals).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

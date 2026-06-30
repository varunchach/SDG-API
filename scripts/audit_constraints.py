#!/usr/bin/env python3
"""Audit generated records against spec/BRE operational ranges."""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from faker import Faker

from src.generators.constraints import validate_record_constraints
from src.generators.customer import generate_customer_record
from src.generators.scenarios import SCENARIO_NAMES
from src.generators.uniqueness import IdentityRegistry


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit identifier/value ranges vs constraints.md")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--per-scenario", type=int, default=5, help="Records per scenario")
    args = parser.parse_args()

    all_errors: list[str] = []
    total = 0

    print("Constraint range audit\n")
    for scenario in SCENARIO_NAMES:
        rng = random.Random(args.seed + hash(scenario) % 1000)
        faker = Faker("en_IN")
        faker.seed_instance(args.seed)
        registry = IdentityRegistry()
        scenario_errors = 0

        for i in range(1, args.per_scenario + 1):
            total += 1
            rec = generate_customer_record(
                rng, faker, registry, record_id=i, scenario=scenario
            )
            errs = validate_record_constraints(rec)
            if errs:
                scenario_errors += len(errs)
                all_errors.extend(f"[{scenario}/{rec['recordId']}] {e}" for e in errs)

        status = "OK" if scenario_errors == 0 else f"{scenario_errors} issue(s)"
        print(f"  {scenario:<20} {args.per_scenario} records — {status}")

    print(f"\nTotal records: {total}, constraint violations: {len(all_errors)}")
    if all_errors:
        print("\nSample violations:")
        for e in all_errors[:15]:
            print(f"  - {e}")
        return 1

    print("All identifiers and values are within operational ranges.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

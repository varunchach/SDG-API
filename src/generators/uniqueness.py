"""Track essential identity fields — no duplicates within a batch."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class IdentityRegistry:
    pans: set[str] = field(default_factory=set)
    mobiles: set[str] = field(default_factory=set)
    emails: set[str] = field(default_factory=set)
    customer_ids: set[str] = field(default_factory=set)
    partner_journey_ids: set[str] = field(default_factory=set)
    bank_journey_ids: set[str] = field(default_factory=set)
    orc_journey_ids: set[str] = field(default_factory=set)

    def audit_records(self, records: list[dict]) -> list[str]:
        """Return duplicate-field errors across a generated batch."""
        errors: list[str] = []
        fields = {
            "pan": [],
            "mobile": [],
            "email": [],
            "customerId": [],
            "partnerJourneyID": [],
            "bankJourneyID": [],
            "orcJourneyID": [],
        }
        for rec in records:
            p = rec["profile"]
            j = rec["journey"]
            fields["pan"].append(p["pan"])
            fields["mobile"].append(p["mobile"])
            fields["email"].append(p["email"])
            fields["customerId"].append(p["customerId"])
            fields["partnerJourneyID"].append(j["partnerJourneyID"])
            fields["bankJourneyID"].append(j["bankJourneyID"])
            fields["orcJourneyID"].append(j["orcJourneyID"])

        for name, values in fields.items():
            seen: set[str] = set()
            dups: set[str] = set()
            for v in values:
                if v in seen:
                    dups.add(v)
                seen.add(v)
            if dups:
                errors.append(f"duplicate {name}: {sorted(dups)[:5]}")
        return errors

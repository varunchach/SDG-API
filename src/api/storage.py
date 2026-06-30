"""In-memory journey store with thread-safe access."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class JourneyRecord:
    orc_journey_id: str
    partner_journey_id: str
    bank_journey_id: str
    scenario: str
    initiate_request: dict[str, Any]
    ack_response: dict[str, Any]
    callback_order: list[str]
    callbacks: dict[str, Any] = field(default_factory=dict)
    status: str = "INITIATED"  # INITIATED | IN_PROGRESS | COMPLETED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    def to_status_dict(self) -> dict[str, Any]:
        pending = [c for c in self.callback_order if c not in self.callbacks]
        return {
            "orcJourneyID": self.orc_journey_id,
            "partnerJourneyID": self.partner_journey_id,
            "bankJourneyID": self.bank_journey_id,
            "scenario": self.scenario,
            "status": self.status,
            "createdAt": self.created_at.isoformat(),
            "completedAt": self.completed_at.isoformat() if self.completed_at else None,
            "callbackOrder": self.callback_order,
            "callbacksReceived": list(self.callbacks.keys()),
            "callbacksPending": pending,
            "ackResponse": self.ack_response,
            "callbacks": self.callbacks,
        }


class JourneyStore:
    def __init__(self) -> None:
        self._by_orc: dict[str, JourneyRecord] = {}
        self._lock = threading.Lock()

    def save(self, record: JourneyRecord) -> None:
        with self._lock:
            self._by_orc[record.orc_journey_id] = record

    def get(self, orc_journey_id: str) -> JourneyRecord | None:
        with self._lock:
            return self._by_orc.get(orc_journey_id)

    def add_callback(self, orc_journey_id: str, report_type: str, payload: dict[str, Any]) -> None:
        with self._lock:
            rec = self._by_orc.get(orc_journey_id)
            if not rec:
                return
            rec.callbacks[report_type] = payload
            rec.status = "IN_PROGRESS"
            if set(rec.callback_order) <= set(rec.callbacks.keys()):
                rec.status = "COMPLETED"
                rec.completed_at = datetime.now(timezone.utc)

    def list_all(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {
                    "orcJourneyID": r.orc_journey_id,
                    "partnerJourneyID": r.partner_journey_id,
                    "scenario": r.scenario,
                    "status": r.status,
                    "createdAt": r.created_at.isoformat(),
                    "callbacksReceived": len(r.callbacks),
                    "callbacksTotal": len(r.callback_order),
                }
                for r in sorted(self._by_orc.values(), key=lambda x: x.created_at, reverse=True)
            ]


store = JourneyStore()

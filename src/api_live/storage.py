"""Live journey store — extends demo store with profile + CSV hook."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable


@dataclass
class LiveJourneyRecord:
    record_id: str
    orc_journey_id: str
    partner_journey_id: str
    bank_journey_id: str
    scenario: str
    profile: dict[str, Any]
    initiate_request: dict[str, Any]
    ack_response: dict[str, Any]
    callback_order: list[str]
    callbacks: dict[str, Any] = field(default_factory=dict)
    status: str = "INITIATED"
    csv_saved: bool = False
    csv_location: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    def to_status_dict(self) -> dict[str, Any]:
        pending = [c for c in self.callback_order if c not in self.callbacks]
        return {
            "recordId": self.record_id,
            "orcJourneyID": self.orc_journey_id,
            "partnerJourneyID": self.partner_journey_id,
            "bankJourneyID": self.bank_journey_id,
            "scenario": self.scenario,
            "profile": self.profile,
            "status": self.status,
            "csvSaved": self.csv_saved,
            "csvLocation": self.csv_location,
            "createdAt": self.created_at.isoformat(),
            "completedAt": self.completed_at.isoformat() if self.completed_at else None,
            "callbackOrder": self.callback_order,
            "callbacksReceived": list(self.callbacks.keys()),
            "callbacksPending": pending,
            "ackResponse": self.ack_response,
            "callbacks": self.callbacks,
        }


class LiveJourneyStore:
    def __init__(self) -> None:
        self._by_orc: dict[str, LiveJourneyRecord] = {}
        self._lock = threading.Lock()
        self._on_complete: Callable[[LiveJourneyRecord], None] | None = None

    def set_on_complete(self, handler: Callable[[LiveJourneyRecord], None]) -> None:
        self._on_complete = handler

    def save(self, record: LiveJourneyRecord) -> None:
        with self._lock:
            self._by_orc[record.orc_journey_id] = record

    def get(self, orc_journey_id: str) -> LiveJourneyRecord | None:
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
                if self._on_complete and not rec.csv_saved:
                    self._on_complete(rec)


live_store = LiveJourneyStore()

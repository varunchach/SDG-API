"""Load pre-generated customer records for UI prefill."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
GENERATED_DIR = ROOT / "data" / "generated"


def list_records() -> list[dict[str, Any]]:
    index_path = GENERATED_DIR / "customers-index.json"
    if not index_path.exists():
        return []
    return json.loads(index_path.read_text(encoding="utf-8"))


def load_record(record_id: str) -> dict[str, Any] | None:
    path = GENERATED_DIR / "customers" / f"{record_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))

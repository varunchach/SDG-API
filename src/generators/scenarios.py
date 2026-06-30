"""Load scenario behaviour overrides from data/scenarios/*.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS_DIR = ROOT / "data" / "scenarios"

SCENARIO_NAMES = (
    "clean-approval",
    "thin-file",
    "fraud-hit",
    "posidex-match",
    "bureau-not-found",
)

_cache: dict[str, dict[str, Any]] = {}


def load_scenario(name: str) -> dict[str, Any]:
    if name not in SCENARIO_NAMES:
        raise ValueError(f"Unknown scenario: {name}. Choose from {SCENARIO_NAMES}")
    if name not in _cache:
        path = SCENARIOS_DIR / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(f"Scenario file missing: {path}")
        _cache[name] = json.loads(path.read_text(encoding="utf-8"))
    return deep_copy_scenario(_cache[name])


def deep_copy_scenario(data: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(data))


def list_scenarios() -> list[str]:
    return list(SCENARIO_NAMES)

"""Load producer callback templates from EE spec .txt sample files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SPEC_DIR = ROOT / "EligibilityEngine_SpecDoc_SampleFiles"

CALLBACK_TXT: dict[str, str] = {
    "mbCibil": "mbCibil Sample Callback.txt",
    "mbEquifax": "mbEquifax Sample Callback.txt",
    "mbHighMark": "mbHighMark Sample Callback.txt",
    "mbMbEot": "mbMbEot Sample Callback.txt",
    "perfios": "perfios Sample Callback.txt",
    "perfios-body": "perfios Sample Callback.txt",
    "posidex": "posidex Sample Callback.txt",
    "hunter": "hunter Sample Callback.txt",
    "summary": "summary Sample Callback.txt",
}

INITIATE_REQUEST_TXT = "EE- initiate request V1.0.txt"


def load_spec_initiate_request() -> Any:
    """Load partner initiate JSON from EE- initiate request V1.0.txt."""
    path = SPEC_DIR / INITIATE_REQUEST_TXT
    if not path.exists():
        raise FileNotFoundError(f"Spec initiate request not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_spec_callback(name: str) -> Any:
    """Load callback JSON from EligibilityEngine_SpecDoc_SampleFiles/*.txt."""
    filename = CALLBACK_TXT.get(name)
    if not filename:
        raise FileNotFoundError(f"No spec .txt mapping for callback: {name}")
    path = SPEC_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Spec callback not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def posidex_template_row_count() -> int:
    return len(load_spec_callback("posidex")["posidex"]["outputdata"])

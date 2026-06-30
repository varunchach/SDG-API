#!/usr/bin/env python3
"""Start the mock Eligibility Engine API + UI."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import uvicorn

if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", "8000"))
    reload = os.environ.get("RELOAD", "1") == "1"
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=port,
        reload=reload,
    )

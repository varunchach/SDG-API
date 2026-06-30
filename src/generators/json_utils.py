"""JSON template helpers — deep copy, path get/set, template loading."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = ROOT / "data" / "templates"
CALLBACKS_DIR = TEMPLATES_DIR / "callbacks"

_PATH_PART = re.compile(r"^([^[\]]+)(?:\[(\d+)\])?$")


def deep_copy(obj: Any) -> Any:
    return copy.deepcopy(obj)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_template(name: str) -> Any:
    """Load a template by name from data/templates/ or callbacks/."""
    if name.endswith(".json"):
        candidates = [TEMPLATES_DIR / name, CALLBACKS_DIR / name]
    elif name in (
        "initiate-request",
        "ack-response",
    ):
        candidates = [TEMPLATES_DIR / f"{name}.json"]
    else:
        candidates = [CALLBACKS_DIR / f"{name}.json"]
    for path in candidates:
        if path.exists():
            return load_json(path)
    raise FileNotFoundError(f"Template not found: {name}")


def _parse_part(part: str) -> tuple[str, int | None]:
    m = _PATH_PART.match(part)
    if not m:
        raise ValueError(f"Invalid path segment: {part}")
    return m.group(1), int(m.group(2)) if m.group(2) is not None else None


def get_path(obj: Any, path: str) -> Any:
    current = obj
    for part in path.split("."):
        key, idx = _parse_part(part)
        current = current[key] if idx is None else current[key][idx]
    return current


def set_path(obj: Any, path: str, value: Any) -> None:
    parts = path.split(".")
    current = obj
    for part in parts[:-1]:
        key, idx = _parse_part(part)
        current = current[key] if idx is None else current[key][idx]
    last_key, last_idx = _parse_part(parts[-1])
    if last_idx is None:
        current[last_key] = value
    else:
        current[last_key][last_idx] = value


def collect_keys(obj: Any, prefix: str = "") -> set[str]:
    """Collect all leaf key paths (dot-separated) from a nested dict/list structure."""
    keys: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else k
            if isinstance(v, (dict, list)):
                keys.update(collect_keys(v, path))
            else:
                keys.add(path)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            path = f"{prefix}[{i}]"
            if isinstance(item, (dict, list)):
                keys.update(collect_keys(item, path))
            else:
                keys.add(path)
    return keys


def keys_match(template: Any, generated: Any, *, label: str = "") -> list[str]:
    """Return list of key-path mismatches between template and generated JSON."""
    t_keys = collect_keys(template)
    g_keys = collect_keys(generated)
    missing = sorted(t_keys - g_keys)
    extra = sorted(g_keys - t_keys)
    errors: list[str] = []
    prefix = f"{label}: " if label else ""
    if missing:
        errors.append(f"{prefix}missing keys ({len(missing)}): {missing[:5]}{'...' if len(missing) > 5 else ''}")
    if extra:
        errors.append(f"{prefix}extra keys ({len(extra)}): {extra[:5]}{'...' if len(extra) > 5 else ''}")
    return errors

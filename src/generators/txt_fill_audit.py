"""Audit generated callbacks against non-empty fields in spec .txt samples."""

from __future__ import annotations

from typing import Any

from .json_utils import get_path
from .nonempty_filler import collect_all_nonempty_paths
from .spec_templates import load_spec_callback

# Known spec sample literals that must never appear in generated output.
SAMPLE_LITERAL_BLOCKLIST = (
    "NABANITA PAL",
    "NIKUNJ KUMAR AND CO",
    "NARAYANBHAI SHIVRAMBHAI PATEL",
    "shangu@perfios.com",
    "Shangu Shiva",
    "ABDCE1234F",
    "AAOPP1630R",
    "801598078",
    "18703457",
    "Acme Bank Ltd., India",
    "BS5177628815",
    "PRB0000003",
)

PRODUCERS = (
    "mbCibil",
    "mbEquifax",
    "mbHighMark",
    "mbMbEot",
    "perfios",
    "posidex",
    "hunter",
    "summary",
)


def _generated_root(name: str, callbacks: dict[str, Any]) -> Any:
    if name == "perfios":
        return callbacks["perfios"]["perfios"]
    return callbacks[name]


def validate_txt_nonempty_coverage(callbacks: dict[str, Any]) -> list[str]:
    """
    Strict check: every non-empty leaf in spec .txt must exist in generated output
    and must not be blank.
    """
    errors: list[str] = []
    for name in PRODUCERS:
        template = load_spec_callback(name if name != "perfios" else "perfios")
        generated = _generated_root(name, callbacks)
        for path, template_val in collect_all_nonempty_paths(template):
            try:
                value = get_path(generated, path)
            except (KeyError, IndexError, TypeError, ValueError):
                errors.append(f"{name}: missing path {path} (template had {template_val!r})")
                continue
            if value in (None, ""):
                errors.append(f"{name}: empty at {path} (template had {template_val!r})")
    return errors


def aligned_paths(
    template: Any,
    generated: Any,
    prefix: str = "",
) -> list[tuple[str, str, str]]:
    """(path, template_value, generated_value) for aligned template/generated trees."""
    rows: list[tuple[str, str, str]] = []
    if isinstance(template, dict) and isinstance(generated, dict):
        for key, t_val in template.items():
            if key not in generated:
                continue
            child = f"{prefix}.{key}" if prefix else key
            rows.extend(aligned_paths(t_val, generated[key], child))
    elif isinstance(template, list) and isinstance(generated, list):
        for i in range(min(len(template), len(generated))):
            rows.extend(aligned_paths(template[i], generated[i], f"{prefix}[{i}]"))
    else:
        t_str = "" if template is None else str(template)
        g_str = "" if generated is None else str(generated)
        if t_str:
            rows.append((prefix, t_str, g_str))
    return rows


def audit_callbacks(callbacks: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Per-producer stats using full template tree coverage."""
    report: dict[str, dict[str, Any]] = {}
    for name in PRODUCERS:
        template = load_spec_callback(name if name != "perfios" else "perfios")
        generated = _generated_root(name, callbacks)
        all_paths = collect_all_nonempty_paths(template)
        empty_paths: list[str] = []
        missing_paths: list[str] = []
        static_paths: list[str] = []
        generated_count = 0
        for path, t_val in all_paths:
            try:
                g_val = get_path(generated, path)
                g_str = "" if g_val is None else str(g_val)
            except (KeyError, IndexError, TypeError, ValueError):
                missing_paths.append(path)
                continue
            if not g_str:
                empty_paths.append(path)
            elif g_str == t_val:
                static_paths.append(path)
            else:
                generated_count += 1
        total = len(all_paths)
        report[name] = {
            "total": total,
            "generated": generated_count,
            "empty": len(empty_paths),
            "missing": len(missing_paths),
            "static": len(static_paths),
            "empty_paths": empty_paths[:10],
            "missing_paths": missing_paths[:10],
            "static_paths": static_paths[:10],
            "generated_pct": round(100 * generated_count / total, 1) if total else 100.0,
            "empty_pct": round(100 * len(empty_paths) / total, 1) if total else 0.0,
            "missing_pct": round(100 * len(missing_paths) / total, 1) if total else 0.0,
        }
    return report


def find_blocklisted_literals(callbacks: dict[str, Any]) -> list[str]:
    import json

    blob = json.dumps(callbacks)
    return [lit for lit in SAMPLE_LITERAL_BLOCKLIST if lit in blob]


def validate_semantic_fills(callbacks: dict[str, Any], profile: dict[str, Any]) -> list[str]:
    """Catch bureau fields incorrectly filled with applicant identity."""
    errors: list[str] = []
    full = profile.get("fullName", "")

    def walk(obj, prefix=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                yield from walk(v, f"{prefix}.{k}" if prefix else k)
        elif isinstance(obj, list):
            for i, x in enumerate(obj):
                yield from walk(x, f"{prefix}[{i}]")
        else:
            yield prefix, obj

    for path, val in walk(callbacks):
        if val != full or not full:
            continue
        leaf = path.split(".")[-1].split("[")[0]
        if leaf in {"SOURCE_NAME", "SOA_SOURCE_NAME", "MEMBER_NAME"}:
            errors.append(f"{leaf} must not be applicant name at {path}")
    return errors


def validate_callbacks_filled(callbacks: dict[str, Any], profile: dict[str, Any] | None = None) -> list[str]:
    """Return errors if any spec .txt non-empty field is missing, blank, or blocklisted."""
    errors: list[str] = []
    errors.extend(f"blocklisted sample literal: {lit}" for lit in find_blocklisted_literals(callbacks))
    if profile:
        errors.extend(validate_semantic_fills(callbacks, profile))
    errors.extend(validate_txt_nonempty_coverage(callbacks))
    return errors

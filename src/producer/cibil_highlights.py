"""Backward-compatible re-export — use producer_highlights.py."""

from .producer_highlights import extract_cibil_highlights, extract_mb_cibil_highlights

__all__ = ["extract_cibil_highlights", "extract_mb_cibil_highlights"]

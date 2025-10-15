"""Utility helpers for normalising Seoul open API payloads."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from typing import Any, Iterable

_SPACE_RE = re.compile(r"\s+")
_LOT_RE = re.compile(r"[^0-9-]")


def normalize_text(value: str | None) -> str | None:
    """Return a compact, lower-cased string or ``None`` for empty input."""

    if not value:
        return None
    normalized = _SPACE_RE.sub("", value).strip().lower()
    return normalized or None


def normalize_lot(value: str | None) -> str | None:
    """Keep only digits and hyphen for lot/parcel identifiers."""

    if not value:
        return None
    cleaned = _LOT_RE.sub("", value)
    return cleaned or None


def parse_yyyymmdd(value: str | None) -> date | None:
    """Convert a Seoul ``YYYYMMDD`` string into :class:`datetime.date`."""

    if not value:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(trimmed[:10], fmt).date()
        except ValueError:
            continue
    return None


def stable_bigint_id(*parts: Iterable[Any] | Any) -> int:
    """Generate a deterministic 64-bit integer identifier from arbitrary data."""

    def _to_json(value: Any) -> str:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)

    if len(parts) == 1:
        payload = parts[0]
    else:
        payload = parts
    raw = _to_json(payload)
    digest = hashlib.blake2b(raw.encode("utf-8"), digest_size=8)
    return int.from_bytes(digest.digest(), "big", signed=False)


__all__ = [
    "normalize_text",
    "normalize_lot",
    "parse_yyyymmdd",
    "stable_bigint_id",
]

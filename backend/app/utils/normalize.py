"""Utility helpers for normalising Seoul open API payloads."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Optional

_SPACE_RE = re.compile(r"\s+")
_LOT_RE = re.compile(r"[^0-9-]")
_NON_DIGIT_RE = re.compile(r"\D")


def norm_text(value: Optional[str]) -> Optional[str]:
    """Return a compact, lower-cased string or ``None`` for empty input."""
    if not value:
        return None
    normalized = _SPACE_RE.sub("", str(value)).strip().lower()
    return normalized or None


def clean_lot_jibun(value: Optional[str]) -> Optional[str]:
    """Keep only digits and hyphen for lot/parcel identifiers."""
    if not value:
        return None
    cleaned = _LOT_RE.sub("", str(value))
    return cleaned or None


def yyyymmdd_to_date(value: Optional[str]) -> Optional[date]:
    """Convert a Seoul ``YYYYMMDD`` string into :class:`datetime.date`."""
    if not value:
        return None
    trimmed = str(value).strip()
    if not trimmed:
        return None
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(trimmed[:10], fmt).date()
        except ValueError:
            continue
    digits = _NON_DIGIT_RE.sub("", trimmed)
    if len(digits) >= 8:
        try:
            return datetime.strptime(digits[:8], "%Y%m%d").date()
        except ValueError:
            return None
    return None


def mwon_to_krw(value: object) -> Optional[int]:
    """Convert values expressed in million-won (만원) into KRW (원) as int.

    - 단위는 그대로: 만원 → 원(× 10,000)
    - 쉼표/공백 허용: "12,345" -> 123450000
    - 부동소수 오차 방지를 위해 Decimal 사용
    """
    if value in (None, ""):
        return None
    s = str(value).strip().replace(",", "")
    if s == "":
        return None
    try:
        won = (Decimal(s) * Decimal(10000)).to_integral_value()  # 정수 결과
        return int(won)
    except (InvalidOperation, ValueError, TypeError):
        return None


def normalize_text(value: Optional[str]) -> Optional[str]:
    """Backward compatible wrapper for :func:`norm_text`."""
    return norm_text(value)


def normalize_lot(value: Optional[str]) -> Optional[str]:
    """Backward compatible wrapper for :func:`clean_lot_jibun`."""
    return clean_lot_jibun(value)


def parse_yyyymmdd(value: Optional[str]) -> Optional[date]:
    """Backward compatible wrapper for :func:`yyyymmdd_to_date`."""
    return yyyymmdd_to_date(value)


def stable_bigint_id(*parts: Iterable[Any] | Any) -> int:
    """Generate a deterministic BIGINT-safe (signed 63-bit) integer from arbitrary data."""
    def _to_json(value: Any) -> str:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)

    payload = parts[0] if len(parts) == 1 else parts
    raw = _to_json(payload)
    digest = hashlib.blake2b(raw.encode("utf-8"), digest_size=8).digest()
    val = int.from_bytes(digest, "big", signed=False)
    # Postgres BIGINT(signed) 범위 보장을 위해 63bit 마스킹 (최대 2^63-1)
    val &= (1 << 63) - 1
    return val or 1  # 극저확률 0 방지

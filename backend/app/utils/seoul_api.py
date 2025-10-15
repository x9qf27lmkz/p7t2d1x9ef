"""Minimal wrapper around the Seoul open data API."""
from __future__ import annotations

import math
import os
import time
from typing import Generator, Iterable, List

import requests

_DEFAULT_PAGE_SIZE = 1000
_DEFAULT_THROTTLE_SECONDS = 0.2
_BASE_URL = "http://openapi.seoul.go.kr:8088"


class SeoulApiError(RuntimeError):
    """Raised when the Seoul open API returns an unexpected payload."""


def _resolve_api_key() -> str:
    try:
        return os.environ["SEOUL_API_KEY"]
    except KeyError as exc:  # pragma: no cover - simple env lookup
        raise SeoulApiError("SEOUL_API_KEY is not configured") from exc


def iter_rows(
    service: str,
    *,
    api_key: str | None = None,
    page_size: int = _DEFAULT_PAGE_SIZE,
    throttle_seconds: float = _DEFAULT_THROTTLE_SECONDS,
) -> Generator[List[dict], None, None]:
    """Yield batches of rows for the given service."""

    key = api_key or _resolve_api_key()
    first_url = f"{_BASE_URL}/{key}/json/{service}/1/1"
    response = requests.get(first_url, timeout=30)
    response.raise_for_status()
    payload = response.json()
    service_block = payload.get(service) or {}
    total_count = service_block.get("list_total_count")

    if total_count is None:
        raise SeoulApiError(f"Could not determine list_total_count for {service}")

    pages = max(1, math.ceil(int(total_count) / page_size))
    for page in range(pages):
        start = page * page_size + 1
        end = (page + 1) * page_size
        url = f"{_BASE_URL}/{key}/json/{service}/{start}/{end}"
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        batch_payload = response.json().get(service) or {}
        rows: Iterable[dict] = batch_payload.get("row") or []
        yield list(rows)
        time.sleep(throttle_seconds)


__all__ = [
    "SeoulApiError",
    "iter_rows",
]

"""Minimal wrapper around the Seoul open data API."""
from __future__ import annotations

import math
import os
import time
from typing import Any, Dict, Generator, Iterable, List, Optional

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


def _json(response: requests.Response) -> Dict[str, Any]:
    response.raise_for_status()
    try:
        return response.json()
    except ValueError as exc:  # pragma: no cover - network JSON parsing
        raise SeoulApiError(f"Invalid JSON payload: {response.text[:200]}") from exc


def _find_row(obj: Any) -> Optional[List[Dict[str, Any]]]:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key.lower() == "row" and isinstance(value, list):
                return value
            if isinstance(value, (dict, list)):
                found = _find_row(value)
                if found is not None:
                    return found
    elif isinstance(obj, list):
        for item in obj:
            found = _find_row(item)
            if found is not None:
                return found
    return None


def list_total_count(payload: Any) -> int:
    """Extract the ``list_total_count`` value from the Seoul payload."""

    if isinstance(payload, dict):
        for key, value in payload.items():
            if key.lower() == "list_total_count":
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return 0
            if isinstance(value, (dict, list)):
                count = list_total_count(value)
                if count:
                    return count
    elif isinstance(payload, list):
        for item in payload:
            count = list_total_count(item)
            if count:
                return count
    return 0


def probe_service(api_key: str, candidates: Iterable[str]) -> str:
    """Return the first working service name from ``candidates``."""

    for service in candidates:
        url = f"{_BASE_URL}/{api_key}/json/{service}/1/1"
        try:
            payload = _json(requests.get(url, timeout=10))
        except Exception:  # pragma: no cover - network failure fallback
            continue
        if list_total_count(payload) >= 0:
            return service
    raise SeoulApiError(f"Service not detected among {list(candidates)}")


def fetch_pages(
    api_key: Optional[str],
    service: str,
    *,
    page_size: int = _DEFAULT_PAGE_SIZE,
    throttle_seconds: float = _DEFAULT_THROTTLE_SECONDS,
) -> Generator[List[Dict[str, Any]], None, None]:
    """Yield batches of rows for the given service."""

    key = api_key or _resolve_api_key()
    head = _json(requests.get(f"{_BASE_URL}/{key}/json/{service}/1/1", timeout=30))
    total = list_total_count(head)
    pages = max(1, math.ceil(total / page_size))

    for page in range(pages):
        start = page * page_size + 1
        end = (page + 1) * page_size
        url = f"{_BASE_URL}/{key}/json/{service}/{start}/{end}"
        payload = _json(requests.get(url, timeout=60))
        rows = _find_row(payload) or []
        yield list(rows)
        time.sleep(throttle_seconds)


def iter_rows(
    service: str,
    *,
    api_key: str | None = None,
    page_size: int = _DEFAULT_PAGE_SIZE,
    throttle_seconds: float = _DEFAULT_THROTTLE_SECONDS,
) -> Generator[List[dict], None, None]:
    """Backward compatible wrapper yielding row batches for ``service``."""

    yield from fetch_pages(
        api_key,
        service,
        page_size=page_size,
        throttle_seconds=throttle_seconds,
    )


__all__ = [
    "SeoulApiError",
    "fetch_pages",
    "iter_rows",
    "list_total_count",
    "probe_service",
]

"""Minimal wrapper around the Seoul open data API with robust retries + start_page."""
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
    """Raised when the Seoul open API returns an unexpected or permanent error."""


class SeoulApiTransient(RuntimeError):
    """Raised for transient conditions (timeouts, 5xx, temporary bad payloads)."""


def _resolve_api_key() -> str:
    try:
        return os.environ["SEOUL_API_KEY"]
    except KeyError as exc:  # pragma: no cover
        raise SeoulApiError("SEOUL_API_KEY is not configured") from exc


def _looks_like_server_error(text: str) -> bool:
    t = (text or "").upper()
    return (
        "<CODE>ERROR-500" in t
        or "SERVER ERROR" in t
        or "서버 오류" in t
        or "HTTP OPERATION FAILED" in t
    )


def _json(response: requests.Response) -> Dict[str, Any]:
    """Strict JSON load with classification of transient server-side responses."""
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        if 500 <= response.status_code < 600:
            raise SeoulApiTransient(f"HTTP {response.status_code}") from exc
        raise SeoulApiError(f"HTTP {response.status_code}") from exc

    try:
        return response.json()
    except ValueError as exc:
        text = (response.text or "")
        if _looks_like_server_error(text):
            # non-JSON but clearly a server-side transient error payload
            raise SeoulApiTransient("Server returned non-JSON error payload") from exc
        raise SeoulApiError(f"Invalid JSON payload: {text[:200]}") from exc


def _get_json_with_retry(url: str, *, timeout: float = 60, max_retries: int = 8) -> Dict[str, Any]:
    """Fetch URL and return parsed JSON with exponential backoff on transient errors."""
    base_sleep = 1.0
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, timeout=timeout)
            return _json(resp)
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError, SeoulApiTransient) as e:
            sleep = min(60.0, base_sleep * (2 ** (attempt - 1)))
            print(f"⚠️  SEOUL API transient error on attempt {attempt}/{max_retries}. Sleeping {sleep:.1f}s. URL={url}")
            time.sleep(sleep)
            continue
    raise SeoulApiError(f"❌ Exhausted retries fetching {url}")


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
            payload = _get_json_with_retry(url, timeout=60, max_retries=5)
        except SeoulApiError:
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
    start_page: int = 1,   # ← 추가: 시작 페이지(1-base)
) -> Generator[List[Dict[str, Any]], None, None]:
    """Yield batches of rows for the given service (robust against transient API failures).

    start_page: 1-base 페이지 번호. 이 페이지부터 요청/반환한다.
    """
    key = api_key or _resolve_api_key()

    # 1/1 헤더 조회 (총 건수)
    head_url = f"{_BASE_URL}/{key}/json/{service}/1/1"
    head = _get_json_with_retry(head_url, timeout=60, max_retries=8)
    total = list_total_count(head)
    pages = max(1, math.ceil(total / page_size))

    # 내부 인덱스 보정
    start_idx = max(0, int(start_page) - 1)

    for page in range(start_idx, pages):
        start = page * page_size + 1
        end = (page + 1) * page_size
        url = f"{_BASE_URL}/{key}/json/{service}/{start}/{end}"
        payload = _get_json_with_retry(url, timeout=60, max_retries=8)
        rows = _find_row(payload) or []
        yield list(rows)
        if throttle_seconds > 0:
            time.sleep(throttle_seconds)


def iter_rows(
    service: str,
    *,
    api_key: str | None = None,
    page_size: int = _DEFAULT_PAGE_SIZE,
    throttle_seconds: float = _DEFAULT_THROTTLE_SECONDS,
    start_page: int = 1,
) -> Generator[List[dict], None, None]:
    """Backward compatible wrapper yielding row batches for ``service``."""
    yield from fetch_pages(
        api_key,
        service,
        page_size=page_size,
        throttle_seconds=throttle_seconds,
        start_page=start_page,
    )


__all__ = [
    "SeoulApiError",
    "SeoulApiTransient",
    "fetch_pages",
    "iter_rows",
    "list_total_count",
    "probe_service",
]

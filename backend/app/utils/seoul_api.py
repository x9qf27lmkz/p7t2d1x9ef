"""Seoul OpenAPI 최소 래퍼
- service 문자열에 쿼리스트링 허용 (예: "tbLnOpendataRtmsV?CTRT_DAY=20251017")
- URL은 .../{TYPE}/{SERVICE}/{START}/{END}?qs 형태로 안전하게 조립
- 5xx/네트워크 오류 재시도 + ERROR-301(TYPE 문제) 시 json/JSON 자동 폴백
"""
from __future__ import annotations

import math
import os
import time
from typing import Any, Dict, Generator, Iterable, List, Optional, Tuple

import requests

_DEFAULT_PAGE_SIZE = 1000
_DEFAULT_THROTTLE_SECONDS = 0.2
_BASE_URL = "http://openapi.seoul.go.kr:8088"


class SeoulApiError(RuntimeError):
    """비정상(영구) 오류."""


class SeoulApiTransient(RuntimeError):
    """일시적 오류(재시도 대상)."""


# ---------------- utilities ----------------
def _split_service_and_qs(service: str) -> Tuple[str, str]:
    """
    "ServiceName?A=1&B=2" -> ("ServiceName", "A=1&B=2")
    """
    if "?" in service:
        svc, qs = service.split("?", 1)
        return svc.strip().rstrip("/"), qs.strip().lstrip("?")
    return service.strip().rstrip("/"), ""


def _compose_url(api_key: str, service: str, start: int, end: int, *, type_token: str = "json") -> str:
    """
    service 가 쿼리스트링을 포함하든 말든 올바르게 조립.
    예) service="tbLnOpendataRtmsV?CTRT_DAY=20251017"
        -> ".../{type_token}/tbLnOpendataRtmsV/1/1000?CTRT_DAY=20251017"
    """
    svc, qs = _split_service_and_qs(service)
    base = f"{_BASE_URL}/{api_key}/{type_token}/{svc}/{start}/{end}"
    return f"{base}?{qs}" if qs else base


def _resolve_api_key() -> str:
    key = os.environ.get("SEOUL_API_KEY")
    if not key:
        raise SeoulApiError("SEOUL_API_KEY is not configured")
    return key


def _looks_like_server_error(text: str) -> bool:
    t = (text or "").upper()
    return (
        "<CODE>ERROR-500" in t
        or "SERVER ERROR" in t
        or "서버 오류" in t
        or "HTTP OPERATION FAILED" in t
    )


def _json(response: requests.Response) -> Dict[str, Any]:
    """HTTP 에러와 비JSON 응답을 분류."""
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
            # 서버측 임시 오류로 판정(예: WAS 에러 HTML/XML)
            raise SeoulApiTransient("Server returned non-JSON error payload") from exc
        # ex) ERROR-300/301 같은 XML 메시지 그대로 노출
        raise SeoulApiError(f"Invalid JSON payload: {text[:200]}") from exc


def _get_json_with_retry(url: str, *, timeout: float = 60, max_retries: int = 8) -> Dict[str, Any]:
    """
    URL에서 JSON을 받아 파싱.
    - 5xx/네트워크/임시 오류는 지수 백오프로 재시도
    - ERROR-301(TYPE) 오류일 때는 json/JSON 스위치해서 1회 폴백 시도
    """
    base_sleep = 1.0
    tried_type_flip = False

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, timeout=timeout)
            return _json(resp)

        except SeoulApiError as e:
            # ERROR-301(TYPE) → json/JSON 토글해서 한 번만 재시도
            msg = str(e)
            if ("ERROR-301" in msg) and (("/json/" in url) or ("/JSON/" in url)) and not tried_type_flip:
                tried_type_flip = True
                flipped = url.replace("/json/", "/JSON/") if "/json/" in url else url.replace("/JSON/", "/json/")
                print(f"↻ TYPE fallback due to ERROR-301. Retrying with: {flipped}")
                url = flipped
                continue
            raise

        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError, SeoulApiTransient):
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
    """Seoul payload 내부의 list_total_count 추출."""
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
    """후보 중 정상 동작하는 서비스명을 반환."""
    for service in candidates:
        url = _compose_url(api_key, service, 1, 1, type_token="json")
        try:
            payload = _get_json_with_retry(url, timeout=60, max_retries=5)
        except SeoulApiError:
            continue
        if list_total_count(payload) >= 0:
            return service
    raise SeoulApiError(f"Service not detected among {list(candidates)}")


# ---------------- paging ----------------
def fetch_pages(
    api_key: Optional[str],
    service: str,
    *,
    page_size: int = _DEFAULT_PAGE_SIZE,
    throttle_seconds: float = _DEFAULT_THROTTLE_SECONDS,
    start_page: int = 1,   # 1-based
) -> Generator[List[Dict[str, Any]], None, None]:
    """
    서비스 배치 페이지를 순회하며 row 리스트를 yield.
    service 는 "NAME?A=1&B=2" 형식을 허용.
    """
    key = api_key or _resolve_api_key()

    # 1) HEAD(총건수)
    head_url = _compose_url(key, service, 1, 1, type_token="json")
    head = _get_json_with_retry(head_url, timeout=60, max_retries=8)
    total = list_total_count(head)
    pages = max(1, math.ceil(total / page_size))

    start_idx = max(0, int(start_page) - 1)

    # 2) 페이지 루프
    for page in range(start_idx, pages):
        start = page * page_size + 1
        end = (page + 1) * page_size
        url = _compose_url(key, service, start, end, type_token="json")
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
    """과거 호환 래퍼."""
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

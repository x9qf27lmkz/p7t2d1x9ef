# backend/app/utils/seoul_tail_scanner_v2.py
from __future__ import annotations
import math
import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import requests

from app.utils.normalize import stable_bigint_id

# ------------------------------
# Config
# ------------------------------
_DEFAULT_TIMEOUT = 60.0
_DEFAULT_RETRIES = 3
_DEFAULT_BACKOFF = 0.75  # seconds, exponential backoff base
_DEFAULT_THROTTLE = 0.0  # polite sleep between requests (sec)

# 두 엔드포인트를 순차 폴백: 8088(HTTP) -> 443(HTTPS)
_BASE_URLS: Sequence[str] = (
    "http://openapi.seoul.go.kr:8088",
    "https://openapi.seoul.go.kr:443",
)

__all__ = [
    # 기존 공개 API
    "get_last_page_index",
    "fetch_page",
    "find_anchor_page_forward",
    "find_anchor_page_reverse",
    "plan_incremental_pages_from_anchor",
    "rows_until_anchor",
    # 새로 추가: 임의 id로 페이지/행 찾기
    "locate_page_by_id_forward",
    "locate_page_by_id_reverse",
    "locate_page_by_id",
    "find_page_and_row_by_id",
]

# ------------------------------
# URL helpers
# ------------------------------
def _split_service_and_qs(service: str) -> Tuple[str, str]:
    """
    "tbLnOpendataRentV?A=1&B=2" -> ("tbLnOpendataRentV", "A=1&B=2")
    """
    if "?" in service:
        svc, qs = service.split("?", 1)
        return svc.strip().rstrip("/"), qs.strip().lstrip("?")
    return service.strip().rstrip("/"), ""


def _compose_url(base_url: str, api_key: str, service: str, start: int, end: int, type_token: str) -> str:
    """
    KEY / TYPE(json) / SERVICE / START_INDEX / END_INDEX ?<qs>
    """
    svc, qs = _split_service_and_qs(service)
    core = f"{base_url}/{api_key}/{type_token}/{svc}/{start}/{end}"
    return f"{core}?{qs}" if qs else core


# ------------------------------
# JSON extractors
# ------------------------------
def _extract_row(payload: Any) -> List[Dict[str, Any]]:
    """
    payload 안에서 "row": [ ... ] 리스트를 재귀적으로 찾아서 리턴.
    """
    if isinstance(payload, dict):
        for k, v in payload.items():
            if k.lower() == "row" and isinstance(v, list):
                return v
            if isinstance(v, (dict, list)):
                sub = _extract_row(v)
                if sub:
                    return sub
    elif isinstance(payload, list):
        for it in payload:
            sub = _extract_row(it)
            if sub:
                return sub
    return []


def _extract_total_count(payload: Any) -> int:
    """
    payload 안에서 "list_total_count" 정수 추출.
    """
    if isinstance(payload, dict):
        for k, v in payload.items():
            if k.lower() == "list_total_count":
                try:
                    return int(v)
                except Exception:
                    return 0
            if isinstance(v, (dict, list)):
                n = _extract_total_count(v)
                if n:
                    return n
    elif isinstance(payload, list):
        for it in payload:
            n = _extract_total_count(it)
            if n:
                return n
    return 0


# ------------------------------
# HTTP request core (retry + fallback)
# ------------------------------
def _request_json_with_type_and_host_fallback(
    url_maker: Callable[[str, str], str],  # (base_url, type_token) -> url
    *,
    timeout: float = _DEFAULT_TIMEOUT,
    retries: int = _DEFAULT_RETRIES,
    backoff: float = _DEFAULT_BACKOFF,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    1) base_url을 8088 -> 443 순으로 시도
    2) 각 base_url 마다 /json/ 먼저 → JSON 파싱 실패 & 본문에 TYPE 이슈 흔적 있으면 /JSON/로 재시도
    3) 네트워크/HTTP 에러는 지수 백오프하며 최대 retries 회 재시도
    실패 시 마지막 예외를 올림
    """
    last_exc: Optional[Exception] = None

    for base in _BASE_URLS:
        for type_token in ("json", "JSON"):
            url = url_maker(base, type_token)
            for attempt in range(1, retries + 1):
                try:
                    resp = requests.get(url, timeout=timeout)
                    resp.raise_for_status()
                    try:
                        return resp.json()
                    except ValueError:
                        text = resp.text or ""
                        if ("ERROR-301" in text or "TYPE" in text.upper()) and type_token == "json":
                            if verbose:
                                print(f"[req] TYPE hint detected -> retry with /JSON/ ({base})")
                            break  # 다음 type_token으로
                        raise
                except Exception as e:
                    last_exc = e
                    if attempt < retries:
                        delay = backoff * (2 ** (attempt - 1))
                        if verbose:
                            print(f"[req] retry {attempt}/{retries} after error: {e} (sleep {delay:.2f}s)")
                        time.sleep(delay)
                    else:
                        if verbose:
                            print(f"[req] giving up on url={url} after {retries} attempts. last error: {e}")
            # 다음 type_token 시도
        # 다음 base_url 폴백

    assert last_exc is not None
    raise last_exc


# ------------------------------
# Page fetchers
# ------------------------------
def fetch_page(
    api_key: str,
    service: str,
    page_size: int,
    page_no: int,
    *,
    throttle: float = _DEFAULT_THROTTLE,
    timeout: float = _DEFAULT_TIMEOUT,
    retries: int = _DEFAULT_RETRIES,
    backoff: float = _DEFAULT_BACKOFF,
    verbose: bool = False,
) -> List[Dict[str, Any]]:
    """
    page_no(1-based) 한 페이지만 호출해서 row[] 리스트 반환.
    throttle 만큼 대기 (API 예의).
    """
    start = (page_no - 1) * page_size + 1
    end = page_no * page_size

    def url_maker(base_url: str, type_token: str) -> str:
        return _compose_url(base_url, api_key, service, start, end, type_token)

    if verbose:
        # 네가 쓰던 스타일 그대로
        print(f"[tail-scan] fetch page_no={page_no} start={start} end={end}")

    payload = _request_json_with_type_and_host_fallback(
        url_maker,
        timeout=timeout,
        retries=retries,
        backoff=backoff,
        verbose=verbose,
    )
    rows = _extract_row(payload)

    if throttle > 0:
        time.sleep(throttle)

    return rows or []


def get_last_page_index(
    api_key: str,
    service: str,
    page_size: int,
    *,
    throttle: float = _DEFAULT_THROTTLE,
    timeout: float = _DEFAULT_TIMEOUT,
    retries: int = _DEFAULT_RETRIES,
    backoff: float = _DEFAULT_BACKOFF,
    verbose: bool = True,
) -> int:
    """
    1페이지(1~page_size)를 정상 호출해 payload에서 list_total_count를 추출하고
    이를 기반으로 마지막 페이지 번호를 계산한다.
    (서울시 API는 최신=1 페이지)
    """
    start = 1
    end = page_size

    def url_maker(base_url: str, type_token: str) -> str:
        return _compose_url(base_url, api_key, service, start, end, type_token)

    if verbose:
        print(f"[tail-scan] HEAD request {start}~{end} for total_count...")

    payload = _request_json_with_type_and_host_fallback(
        url_maker,
        timeout=timeout,
        retries=retries,
        backoff=backoff,
        verbose=verbose,
    )

    total = _extract_total_count(payload)
    if verbose:
        print(f"[tail-scan] HEAD total_count={total}")

    if total <= 0:
        if verbose:
            print("[tail-scan] WARN: total_count <= 0, treating dataset as empty")
        return 0

    last_page = max(1, math.ceil(total / page_size))
    if verbose:
        print(f"[tail-scan] computed last_page={last_page}")

    if throttle > 0:
        time.sleep(throttle)
    return last_page


# ------------------------------
# Anchor scanning (DB 앵커 id용)
# ------------------------------
def _page_has_anchor(rows: Iterable[Dict[str, Any]], anchor_id: int) -> bool:
    for r in rows:
        if stable_bigint_id(dict(r)) == anchor_id:
            return True
    return False


def find_anchor_page_forward(
    api_key: str,
    service: str,
    page_size: int,
    *,
    anchor_id: int,
    max_scan_pages: Optional[int] = None,  # None이면 last_page까지
    throttle: float = _DEFAULT_THROTTLE,
    timeout: float = _DEFAULT_TIMEOUT,
    retries: int = _DEFAULT_RETRIES,
    backoff: float = _DEFAULT_BACKOFF,
    verbose: bool = True,
) -> Optional[int]:
    """
    ★ 최신=1 페이지라는 전제에 맞춘 정순 스캐너 (1 -> 2 -> ...).
    anchor_id를 포함한 페이지 번호를 찾으면 반환, 없으면 None.
    """
    last = get_last_page_index(
        api_key, service, page_size,
        throttle=throttle, timeout=timeout, retries=retries, backoff=backoff, verbose=verbose
    )
    if verbose:
        print(f"[anchor-scan] total last_page={last}")
        print(f"[anchor-scan] locate start: anchor_id={anchor_id} strategy=forward max_scan_pages={max_scan_pages}")
    if last == 0:
        return None

    limit = min(last, max_scan_pages) if max_scan_pages else last
    for page in range(1, limit + 1):
        if verbose:
            print(f"[anchor-scan] checking page={page} (scanned={page-1}/{limit})")
        rows = fetch_page(
            api_key, service, page_size, page,
            throttle=throttle, timeout=timeout, retries=retries, backoff=backoff, verbose=False
        )
        if rows and _page_has_anchor(rows, anchor_id):
            if verbose:
                print(f"[anchor-scan] ✅ match on page={page}")
            return page

    if verbose:
        print(f"[anchor-scan] ❌ not found after scanning {limit} pages from head")
    return None


def find_anchor_page_reverse(
    api_key: str,
    service: str,
    page_size: int,
    *,
    anchor_id: int,
    max_scan_pages: int,
    throttle: float = _DEFAULT_THROTTLE,
    timeout: float = _DEFAULT_TIMEOUT,
    retries: int = _DEFAULT_RETRIES,
    backoff: float = _DEFAULT_BACKOFF,
    verbose: bool = True,
) -> Optional[int]:
    """
    호환용: tail(마지막 페이지)에서 거꾸로 스캔.
    """
    last = get_last_page_index(
        api_key, service, page_size,
        throttle=throttle, timeout=timeout, retries=retries, backoff=backoff, verbose=verbose
    )
    if verbose:
        print(f"[anchor-scan] total last_page={last}")
        print(f"[anchor-scan] locate start: anchor_id={anchor_id} strategy=reverse max_scan_pages={max_scan_pages}")
    if last == 0:
        return None

    scanned = 0
    page = last
    while page >= 1 and scanned < max_scan_pages:
        if verbose:
            print(f"[anchor-scan] checking page={page} (scanned={scanned}/{max_scan_pages})")
        rows = fetch_page(
            api_key, service, page_size, page,
            throttle=throttle, timeout=timeout, retries=retries, backoff=backoff, verbose=False
        )
        if rows and _page_has_anchor(rows, anchor_id):
            if verbose:
                print(f"[anchor-scan] ✅ match on page={page}")
            return page
        page -= 1
        scanned += 1

    if verbose:
        print(f"[anchor-scan] ❌ not found after scanning {scanned} pages from tail")
    return None


# ------------------------------
# Locate arbitrary id (FORCE_* 등 임의 id)
# ------------------------------
def _row_id_equals(r: Dict[str, Any], target_id: int) -> bool:
    try:
        return stable_bigint_id(dict(r)) == target_id
    except Exception:
        return False


def locate_page_by_id_forward(
    api_key: str,
    service: str,
    page_size: int,
    *,
    target_id: int,
    max_scan_pages: Optional[int] = None,
    throttle: float = _DEFAULT_THROTTLE,
    timeout: float = _DEFAULT_TIMEOUT,
    retries: int = _DEFAULT_RETRIES,
    backoff: float = _DEFAULT_BACKOFF,
    verbose: bool = True,
) -> Optional[int]:
    """
    최신=1 기준 정순(1→2→…)으로 target_id가 포함된 페이지 번호를 찾는다.
    """
    last = get_last_page_index(
        api_key, service, page_size,
        throttle=throttle, timeout=timeout, retries=retries, backoff=backoff, verbose=verbose
    )
    if verbose:
        print(f"[anchor-scan] total last_page={last}")
        print(f"[anchor-scan] locate start: target_id={target_id} strategy=forward max_scan_pages={max_scan_pages}")
    if last == 0:
        return None

    limit = min(last, max_scan_pages) if max_scan_pages else last
    for page in range(1, limit + 1):
        if verbose:
            print(f"[anchor-scan] checking page={page} (scanned={page-1}/{limit}) target_id={target_id}")
        rows = fetch_page(
            api_key, service, page_size, page,
            throttle=throttle, timeout=timeout, retries=retries, backoff=backoff, verbose=False
        )
        if rows and any(_row_id_equals(r, target_id) for r in rows):
            if verbose:
                print(f"[anchor-scan] ✅ match on page={page}")
            return page

    if verbose:
        print(f"[anchor-scan] ❌ not found after scanning {limit} pages from head")
    return None


def locate_page_by_id_reverse(
    api_key: str,
    service: str,
    page_size: int,
    *,
    target_id: int,
    max_scan_pages: int,
    throttle: float = _DEFAULT_THROTTLE,
    timeout: float = _DEFAULT_TIMEOUT,
    retries: int = _DEFAULT_RETRIES,
    backoff: float = _DEFAULT_BACKOFF,
    verbose: bool = True,
) -> Optional[int]:
    """
    tail(마지막 페이지)에서 거꾸로 target_id를 찾는다.
    """
    last = get_last_page_index(
        api_key, service, page_size,
        throttle=throttle, timeout=timeout, retries=retries, backoff=backoff, verbose=verbose
    )
    if verbose:
        print(f"[anchor-scan] total last_page={last}")
        print(f"[anchor-scan] locate start: target_id={target_id} strategy=reverse max_scan_pages={max_scan_pages}")
    if last == 0:
        return None

    scanned = 0
    page = last
    while page >= 1 and scanned < max_scan_pages:
        if verbose:
            print(f"[anchor-scan] checking page={page} (scanned={scanned}/{max_scan_pages}) target_id={target_id}")
        rows = fetch_page(
            api_key, service, page_size, page,
            throttle=throttle, timeout=timeout, retries=retries, backoff=backoff, verbose=False
        )
        if rows and any(_row_id_equals(r, target_id) for r in rows):
            if verbose:
                print(f"[anchor-scan] ✅ match on page={page}")
            return page
        page -= 1
        scanned += 1

    if verbose:
        print(f"[anchor-scan] ❌ not found after scanning {scanned} pages from tail")
    return None


def locate_page_by_id(
    api_key: str,
    service: str,
    page_size: int,
    *,
    target_id: int,
    strategy: str = "forward",   # "forward" | "reverse"
    max_scan_pages: Optional[int] = None,  # reverse면 필수(int)
    throttle: float = _DEFAULT_THROTTLE,
    timeout: float = _DEFAULT_TIMEOUT,
    retries: int = _DEFAULT_RETRIES,
    backoff: float = _DEFAULT_BACKOFF,
    verbose: bool = True,
    fallback_to_reverse: bool = True,  # forward 실패 시 reverse 자동 폴백
) -> Optional[int]:
    """
    target_id를 포함하는 '페이지 번호'를 찾는다.
      - strategy="forward": 최신=1 기준 정순 (권장)
      - strategy="reverse": tail에서 역순 (max_scan_pages 필요)
      - fallback_to_reverse=True: forward에서 실패 시 reverse로 한 번 더 시도
    """
    if strategy == "forward":
        page = locate_page_by_id_forward(
            api_key, service, page_size,
            target_id=target_id, max_scan_pages=max_scan_pages,
            throttle=throttle, timeout=timeout, retries=retries, backoff=backoff, verbose=verbose
        )
        if page is not None:
            return page
        if fallback_to_reverse:
            if verbose:
                print("[anchor-scan] not found in forward scan -> fallback to reverse")
            # reverse에는 명시적인 페이지 한도가 필요하므로 없으면 last 전체로 해석
            if not isinstance(max_scan_pages, int) or max_scan_pages <= 0:
                last = get_last_page_index(
                    api_key, service, page_size,
                    throttle=throttle, timeout=timeout, retries=retries, backoff=backoff, verbose=verbose
                )
                max_scan_pages = max(1, last)
            return locate_page_by_id_reverse(
                api_key, service, page_size,
                target_id=target_id, max_scan_pages=int(max_scan_pages),
                throttle=throttle, timeout=timeout, retries=retries, backoff=backoff, verbose=verbose
            )
        return None

    elif strategy == "reverse":
        if not isinstance(max_scan_pages, int) or max_scan_pages <= 0:
            raise ValueError("max_scan_pages(int) is required for strategy='reverse'")
        return locate_page_by_id_reverse(
            api_key, service, page_size,
            target_id=target_id, max_scan_pages=max_scan_pages,
            throttle=throttle, timeout=timeout, retries=retries, backoff=backoff, verbose=verbose
        )
    else:
        raise ValueError("strategy must be 'forward' or 'reverse'")


def find_page_and_row_by_id(
    api_key: str,
    service: str,
    page_size: int,
    *,
    target_id: int,
    strategy: str = "forward",
    max_scan_pages: Optional[int] = None,
    throttle: float = _DEFAULT_THROTTLE,
    timeout: float = _DEFAULT_TIMEOUT,
    retries: int = _DEFAULT_RETRIES,
    backoff: float = _DEFAULT_BACKOFF,
    verbose: bool = True,
) -> Optional[Tuple[int, int, Dict[str, Any]]]:
    """
    target_id가 있는 (page_no, row_index, row_dict) 반환. 없으면 None.
    row_index는 0-based (그 페이지 내 인덱스).
    """
    page = locate_page_by_id(
        api_key, service, page_size,
        target_id=target_id, strategy=strategy, max_scan_pages=max_scan_pages,
        throttle=throttle, timeout=timeout, retries=retries, backoff=backoff, verbose=verbose
    )
    if page is None:
        return None

    rows = fetch_page(
        api_key, service, page_size, page,
        throttle=throttle, timeout=timeout, retries=retries, backoff=backoff, verbose=False
    )
    for idx, r in enumerate(rows):
        if _row_id_equals(r, target_id):
            return page, idx, r
    return None


# ------------------------------
# Incremental plan helpers
# ------------------------------
def rows_until_anchor(rows: List[Dict[str, Any]], anchor_id: int) -> List[Dict[str, Any]]:
    """
    같은 페이지에 앵커가 포함되어 있을 때, 앵커가 등장하기 전까지의 행만 잘라서 반환.
    (1페이지가 최신이므로, 보통 '앵커보다 더 최신' 레코드들만 고름)
    """
    picked: List[Dict[str, Any]] = []
    for r in rows:
        rid = stable_bigint_id(dict(r))
        if rid == anchor_id:
            break
        picked.append(r)
    return picked


def plan_incremental_pages_from_anchor(
    *,
    last_page: int,
    anchor_page: Optional[int],
    include_anchor_page: bool = True,
) -> List[int]:
    """
    최신=1 기준 증분 적재 페이지 계획 생성.
    - anchor_page가 None: 1..last_page 전체 적재
    - include_anchor_page=True: 1..anchor_page 포함
      (앵커 페이지 내 내용은 rows_until_anchor()로 앵커 전까지만 넣는 방식 추천)
    - False면 1..(anchor_page-1)
    """
    if last_page <= 0:
        return []
    if anchor_page is None:
        return list(range(1, last_page + 1))
    if include_anchor_page:
        return list(range(1, anchor_page + 1))
    else:
        end = max(1, anchor_page - 1)
        return list(range(1, end + 1))

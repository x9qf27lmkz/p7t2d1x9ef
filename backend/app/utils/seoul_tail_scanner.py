from __future__ import annotations
import time
import math
import requests
from typing import Any, Dict, List, Optional

from app.utils.normalize import stable_bigint_id

_BASE_URL = "http://openapi.seoul.go.kr:8088"


def _split_service_and_qs(service: str):
    # "tbLnOpendataRentV?A=1&B=2"  -> ("tbLnOpendataRentV", "A=1&B=2")
    if "?" in service:
        svc, qs = service.split("?", 1)
        return svc.strip().rstrip("/"), qs.strip().lstrip("?")
    return service.strip().rstrip("/"), ""


def _compose_url(api_key: str, service: str, start: int, end: int, type_token: str) -> str:
    """
    서울시 OpenAPI URL 조립기.
    KEY / TYPE(json) / SERVICE / START_INDEX / END_INDEX ?<qs>
    """
    svc, qs = _split_service_and_qs(service)
    base = f"{_BASE_URL}/{api_key}/{type_token}/{svc}/{start}/{end}"
    return f"{base}?{qs}" if qs else base


def _extract_row(payload: Any) -> List[Dict[str, Any]]:
    """
    payload 안에서 "row": [ ... ] 리스트를 찾아서 리턴.
    (tbLnOpendataRentV.row, tbLnOpendataRtmsV.row 등 공통 패턴)
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
    payload 안에서 "list_total_count"를 찾아 정수로 돌려준다.
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


def _request_json_with_type_fallback(url_json: str, timeout: float = 60) -> Dict[str, Any]:
    """
    1) url_json (/json/...) 으로 요청
    2) 만약 응답 바디가 XML 형태 ERROR-301 ("TYPE 확인")처럼 오면
       /JSON/ 으로 바꿔서 한 번 더 시도
    3) 둘 다 실패하면 예외를 올린다 (상위에서 그냥 죽여버리게)
    """
    # 1차 시도: /json/
    resp = requests.get(url_json, timeout=timeout)
    resp.raise_for_status()
    try:
        return resp.json()  # 정상적으로 JSON parse되면 바로 리턴
    except ValueError:
        text = resp.text or ""
        # 서울시 API가 종종 xml로 "ERROR-301 TYPE확인" 이런 걸 주는 경우
        if "ERROR-301" in text or "TYPE" in text.upper():
            # 2차 시도: /JSON/ 으로 토글
            url_up = url_json.replace("/json/", "/JSON/")
            resp2 = requests.get(url_up, timeout=timeout)
            resp2.raise_for_status()
            return resp2.json()
        # 그 외의 이유로 json() 실패 → 그냥 예외 던진다
        raise


def _fetch_page_once(
    api_key: str,
    service: str,
    page_size: int,
    page_no: int,
    throttle: float,
    *,
    verbose: bool = False,
) -> List[Dict[str, Any]]:
    """
    page_no(1-based) 한 페이지만 호출해서 row[] 리스트 그대로 반환.
    throttle 만큼 대기해서 API 부하를 조금 낮춘다.
    """
    start = (page_no - 1) * page_size + 1
    end = page_no * page_size
    url_guess = _compose_url(api_key, service, start, end, "json")

    if verbose:
        print(f"[tail-scan] fetch page_no={page_no} start={start} end={end}")

    payload = _request_json_with_type_fallback(url_guess, timeout=60)
    rows = _extract_row(payload)

    if throttle > 0:
        time.sleep(throttle)

    return rows or []


def get_last_page_index(
    api_key: str,
    service: str,
    page_size: int,
    throttle: float,
    *,
    verbose: bool = True,
) -> int:
    """
    ★ 주인님 버전 (개선된 tail 계산)
    - 더 이상 /1/1 같은 변태 호출 안 한다.
    - 대신 "정상적인 첫 페이지(1~page_size)"를 그냥 한 번 불러온다.
      → 이건 우리가 curl로 직접 확인했을 때 빠르게 안정적으로 응답 왔던 패턴.
    - 응답 payload 안에 항상 list_total_count 가 같이 들어있으므로,
      그걸 page_size 로 나눠 마지막 페이지 번호를 구한다.
    - 이 과정이 막히면 오래 버티지 않고 그냥 예외 던져서 상위에서 즉시 종료하게 한다.
    """

    # HEAD 역할: page_no=1 통짜 호출
    start = 1
    end = page_size
    url_head = _compose_url(api_key, service, start, end, "json")

    if verbose:
        print(f"[tail-scan] HEAD request {start}~{end} for total_count...")

    head_payload = _request_json_with_type_fallback(url_head, timeout=60)

    total = _extract_total_count(head_payload)
    if verbose:
        print(f"[tail-scan] HEAD total_count={total}")

    if total <= 0:
        if verbose:
            print("[tail-scan] WARN: total_count <= 0, treating dataset as empty")
        return 0

    last_page = max(1, math.ceil(total / page_size))
    if verbose:
        print(f"[tail-scan] computed last_page={last_page}")

    # throttle 한 번 지켜줌 (API 예의상)
    if throttle > 0:
        time.sleep(throttle)

    return last_page


def find_anchor_page_reverse(
    api_key: str,
    service: str,
    page_size: int,
    throttle: float,
    anchor_id: int,
    max_scan_pages: int,
    *,
    verbose: bool = True,
) -> Optional[int]:
    """
    알고리즘:
    1. get_last_page_index() 로 tail 페이지 번호를 구한다.
    2. tail, tail-1, tail-2 ... 이런 식으로 역순 스캔하면서
       각 row 의 stable_bigint_id(raw) 가 anchor_id 와 일치하는지 체크.
    3. anchor_id 가 나온 페이지 번호를 반환.
    4. max_scan_pages 만큼만 거꾸로 본다. 못 찾으면 None.
    """

    last_page = get_last_page_index(
        api_key,
        service,
        page_size,
        throttle,
        verbose=verbose,
    )

    if verbose:
        print(f"[anchor-scan] total last_page={last_page}")

    if last_page == 0:
        return None

    page = last_page
    scanned = 0

    while page >= 1 and scanned < max_scan_pages:
        if verbose:
            print(f"[anchor-scan] checking page={page} (scanned={scanned}/{max_scan_pages})")

        rows = _fetch_page_once(
            api_key,
            service,
            page_size,
            page,
            throttle,
            verbose=verbose,
        )

        if rows:
            # 각 row → stable_bigint_id() → id 후보
            ids_here = [stable_bigint_id(dict(r)) for r in rows]
            if anchor_id in ids_here:
                if verbose:
                    print(f"[anchor-scan] ✅ match on page={page}")
                return page
        else:
            if verbose:
                print(f"[anchor-scan] (page={page} empty)")

        page -= 1
        scanned += 1

    if verbose:
        print(f"[anchor-scan] ❌ not found after scanning {scanned} pages from tail")
    return None

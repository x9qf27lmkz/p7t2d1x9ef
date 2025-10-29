# -*- coding: utf-8 -*-
from __future__ import annotations

"""Seed the sale table with full API columns (robust cast / dedup / resume)."""

import argparse
import logging
import os
import time
from decimal import Decimal, InvalidOperation
from typing import Iterable, Sequence, Dict, Tuple

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.db_connection import SessionLocal
from app.models.sale import Sale
from app.utils.normalize import (
    clean_lot_jibun,
    mwon_to_krw,
    norm_text,
    stable_bigint_id,
    yyyymmdd_to_date,
)
from app.utils.seoul_api import fetch_pages, probe_service

LOGGER = logging.getLogger(__name__)
SERVICE_CANDIDATES = ("tbLnOpendataRtmsV", "RealEstateSales", "tbLnOpendataRltm")


# --------- helpers ----------
def _none_if_blank(v: object) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s if s != "" else None


def _to_int(v: object) -> int | None:
    s = _none_if_blank(v)
    if s is None:
        return None
    try:
        return int(s)
    except (ValueError, TypeError):
        try:
            return int(Decimal(s))
        except Exception:
            return None


def _to_decimal(v: object) -> Decimal | None:
    s = _none_if_blank(v)
    if s is None:
        return None
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError, TypeError):
        return None


def _lot_from(row: dict) -> str | None:
    main, sub = _none_if_blank(row.get("MNO")), _none_if_blank(row.get("SNO"))
    if main is None or main == "0":
        return None
    lot = main
    if sub and sub != "0":
        lot = f"{lot}-{sub}"
    return clean_lot_jibun(lot)


def _coords(_: dict) -> Tuple[Decimal | None, Decimal | None]:
    # 매매 API에는 좌표가 사실상 없음(확장 대비)
    return None, None


def _transform_row(row: dict) -> dict:
    """API 원본 -> DB 스키마 1:1 + 파생값 변환"""
    raw = dict(row)

    # 날짜/숫자 캐스팅
    ctrt_day = yyyymmdd_to_date(_none_if_blank(row.get("CTRT_DAY")))
    thing_amt = mwon_to_krw(_none_if_blank(row.get("THING_AMT")))  # 만원 → 원
    arch_area = _to_decimal(row.get("ARCH_AREA"))
    land_area = _to_decimal(row.get("LAND_AREA"))

    lat, lng = _coords(row)

    return {
        # PK
        "id": stable_bigint_id(raw),

        # 원본(공식 스펙 순서)
        "rcpt_yr": _to_int(row.get("RCPT_YR")),
        "cgg_cd": _to_int(row.get("CGG_CD")),
        "cgg_nm": _none_if_blank(row.get("CGG_NM")),
        "stdg_cd": _to_int(row.get("STDG_CD")),
        "stdg_nm": _none_if_blank(row.get("STDG_NM")),
        "lotno_se": _to_int(row.get("LOTNO_SE")),                # 빈문자 → None 처리
        "lotno_se_nm": _none_if_blank(row.get("LOTNO_SE_NM")),
        "mno": _none_if_blank(row.get("MNO")),
        "sno": _none_if_blank(row.get("SNO")),
        "bldg_nm": _none_if_blank(row.get("BLDG_NM")),

        "ctrt_day": ctrt_day,                                    # DATE
        "thing_amt": thing_amt,                                  # BIGINT(원)
        "arch_area": arch_area,                                  # NUMERIC
        "land_area": land_area,                                  # NUMERIC
        "flr": _none_if_blank(row.get("FLR")),                   # 다양한 표기 → TEXT로 유지
        "rght_se": _none_if_blank(row.get("RGHT_SE")),
        "rtrcn_day": _none_if_blank(row.get("RTRCN_DAY")),       # 취소일: 원문 그대로 텍스트
        "arch_yr": _to_int(row.get("ARCH_YR")),
        "bldg_usg": _none_if_blank(row.get("BLDG_USG")),
        "dclr_se": _none_if_blank(row.get("DCLR_SE")),
        "opbiz_restagnt_sgg_nm": _none_if_blank(row.get("OPBIZ_RESTAGNT_SGG_NM")),

        # 파생키/좌표
        "lat": lat,
        "lng": lng,

        # 탐색/조인 키
        "gu_key": norm_text(row.get("CGG_NM")),
        "dong_key": norm_text(row.get("STDG_NM")),
        "name_key": norm_text(row.get("BLDG_NM")),
        "lot_key": _lot_from(row),

        # 원본 JSON
        "raw": raw,
    }


def _iter_chunks(it: Iterable[dict], n: int) -> Iterable[list[dict]]:
    buf: list[dict] = []
    for x in it:
        buf.append(x)
        if len(buf) >= n:
            yield buf
            buf = []
    if buf:
        yield buf


def _dedup_transformed(rows: Iterable[dict]) -> list[dict]:
    by_id: Dict[int, dict] = {}
    for r in rows:
        v = _transform_row(r)
        by_id[v["id"]] = v
    return list(by_id.values())


def _upsert_rows(session: Session, rows: Sequence[dict], chunk_size: int) -> None:
    if not rows:
        return
    for part in _iter_chunks(rows, chunk_size):
        orig_len = len(part)
        part = _dedup_transformed(part)
        if not part:
            continue

        stmt = insert(Sale).values(part)

        # created_at은 최초값 유지, updated_at은 now() 로만 갱신
        update_map = {
            c.name: getattr(stmt.excluded, c.name)
            for c in Sale.__table__.columns
            if c.name not in ("id", "created_at", "updated_at")
        }
        update_map["updated_at"] = func.now()

        session.execute(
            stmt.on_conflict_do_update(
                index_elements=[Sale.id],
                set_=update_map,
            ),
            execution_options={"synchronize_session": False},
        )
        LOGGER.info("sale upsert chunk=%s (deduped %s rows)", len(part), orig_len - len(part))


# --------- CLI / main ----------
def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Seed 'sale' table from Seoul API")
    p.add_argument("--resume", type=int, default=None, help="시작 페이지(1-base)")
    p.add_argument("--chunk", type=int, default=None, help="DB upsert chunk size")
    p.add_argument("--commit-every", type=int, dest="commit_every", default=None, help="커밋 주기(배치 단위)")
    p.add_argument("--throttle", type=float, default=None, help="API 호출 간 대기(초)")
    p.add_argument("--service", type=str, default=None, help="서비스명 강제(tbLnOpendataRtmsV 등)")
    p.add_argument("--api-key", type=str, default=None, help="서울 API 키 강제")
    return p.parse_args()


def run(service_name: str | None = None, *, api_key: str | None = None) -> None:
    args = _parse_args()

    key = (
        args.api_key
        or api_key
        or os.getenv("SEOUL_API_KEY_SALE")
        or os.getenv("SEOUL_API_KEY")
    )
    if not key:
        raise RuntimeError("SEOUL_API_KEY not set")

    service = (
        args.service
        or service_name
        or os.getenv("SEOUL_SALE_SERVICE")
        or probe_service(key, SERVICE_CANDIDATES)
    )

    commit_every = args.commit_every or int(os.getenv("DB_COMMIT_EVERY", "10"))
    throttle = args.throttle or float(os.getenv("SEOUL_API_THROTTLE", "0.02"))
    resume_from = args.resume or int(os.getenv("SEOUL_RESUME_PAGE", os.getenv("RESUME", "1")))
    chunk = args.chunk or int(os.getenv("DB_UPSERT_CHUNK", os.getenv("CHUNK", "1000")))

    LOGGER.info(
        "settings -> chunk=%s, commit_every=%s, throttle=%.3f, resume_from=%s, service=%s",
        chunk, commit_every, throttle, resume_from, service,
    )

    with SessionLocal() as session:
        t0 = time.time()
        batch_count = 0
        for page_idx, batch in enumerate(
            fetch_pages(key, service, throttle_seconds=throttle, start_page=resume_from),
            start=resume_from,
        ):
            _upsert_rows(session, batch, chunk)
            batch_count = page_idx

            if batch_count % commit_every == 0:
                session.commit()
                LOGGER.info("sale batch %s committed", batch_count)

            if batch_count % 100 == 0:
                LOGGER.info("progress: batch %s done", batch_count)

        session.commit()
        LOGGER.info("sale completed: %s batches in %.1fs", batch_count, time.time() - t0)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()

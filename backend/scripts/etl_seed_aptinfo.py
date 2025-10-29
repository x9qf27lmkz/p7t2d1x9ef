"""Seed the aptinfo table from Seoul OpenAPI (bulk upsert, dedup, resume, retry)."""
from __future__ import annotations

import logging
import os
import time
from decimal import Decimal, InvalidOperation
from typing import Iterable, Sequence, Dict

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.db_connection import SessionLocal
from app.models.aptinfo import AptInfo
from app.utils.normalize import (
    clean_lot_jibun,
    norm_text,
    yyyymmdd_to_date,
)
from app.utils.seoul_api import fetch_pages, probe_service

LOGGER = logging.getLogger(__name__)
SERVICE_CANDIDATES = ("OpenAptInfo", "AptInfo", "ApartmentInfo")


# ---------- helpers ----------
def _to_decimal(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _coords(row: dict) -> tuple[Decimal | None, Decimal | None]:
    # API의 좌표 필드: XCRD(경도=lng), YCRD(위도=lat)
    lat = _to_decimal(row.get("YCRD") or row.get("WGS84_Y") or row.get("Y"))
    lng = _to_decimal(row.get("XCRD") or row.get("WGS84_X") or row.get("X"))
    return lat, lng


def _to_int(value: object) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(str(value).split(".")[0])
    except Exception:
        return None


def _transform_row(row: dict) -> dict:
    """원본 row(dict) → DB 레코드(dict). PK는 apt_cd."""
    raw = dict(row)

    # 날짜 필드 (문자열/타임스탬프 혼재 → 유틸로 흡수)
    use_aprv = yyyymmdd_to_date(row.get("USE_APRV_YMD"))
    mdfcn = yyyymmdd_to_date(row.get("MDFCN_YMD"))
    reg = yyyymmdd_to_date(row.get("REG_YMD"))
    cmpx_aprv = yyyymmdd_to_date(row.get("CMPX_APRV_DAY"))
    cmpx_apld = yyyymmdd_to_date(row.get("CMPX_APLD_DAY"))

    lat, lng = _coords(row)

    return {
        # === PK ===
        "apt_cd": (row.get("APT_CD") or "").strip(),

        # === 식별/인덱스용 키 ===
        "gu_key": norm_text(row.get("SGG_ADDR")),
        "dong_key": norm_text(row.get("EMD_ADDR")),
        "name_key": norm_text(row.get("APT_NM")),
        "lot_key": clean_lot_jibun(row.get("APT_STDG_ADDR")),

        # === 원문 주요 컬럼(모두 스키마에 존재) ===
        "sn": _to_int(row.get("SN")),
        "apt_nm": row.get("APT_NM"),
        "cmpx_clsf": row.get("CMPX_CLSF"),
        "apt_stdg_addr": row.get("APT_STDG_ADDR"),
        "apt_rdn_addr": row.get("APT_RDN_ADDR"),
        "ctpv_addr": row.get("CTPV_ADDR"),
        "sgg_addr": row.get("SGG_ADDR"),
        "emd_addr": row.get("EMD_ADDR"),
        "daddr": row.get("DADDR"),
        "rdn_addr": row.get("RDN_ADDR"),
        "road_daddr": row.get("ROAD_DADDR"),
        "telno": row.get("TELNO"),
        "fxno": row.get("FXNO"),
        "apt_cmpx": row.get("APT_CMPX"),
        "apt_atch_file": row.get("APT_ATCH_FILE"),
        "hh_type": row.get("HH_TYPE"),
        "mng_mthd": row.get("MNG_MTHD"),
        "road_type": row.get("ROAD_TYPE"),
        "mn_mthd": row.get("MN_MTHD"),
        "whol_dong_cnt": _to_int(row.get("WHOL_DONG_CNT")),
        "tnohsh": _to_int(row.get("TNOHSH")),
        "bldr": row.get("BLDR"),
        "dvlr": row.get("DVLR"),

        "use_aprv_ymd": use_aprv,

        "gfa": _to_decimal(row.get("GFA")),
        "rsdt_xuar": _to_decimal(row.get("RSDT_XUAR")),
        "mnco_levy_area": _to_decimal(row.get("MNCO_LEVY_AREA")),
        "xuar_hh_stts60": _to_decimal(row.get("XUAR_HH_STTS60")),
        "xuar_hh_stts85": _to_decimal(row.get("XUAR_HH_STTS85")),
        "xuar_hh_stts135": _to_decimal(row.get("XUAR_HH_STTS135")),
        "xuar_hh_stts136": _to_decimal(row.get("XUAR_HH_STTS136")),

        "hmpg": row.get("HMPG"),
        "reg_ymd": reg,
        "mdfcn_ymd": mdfcn,
        "epis_mng_no": row.get("EPIS_MNG_NO"),
        "eps_mng_form": row.get("EPS_MNG_FORM"),
        "hh_elct_ctrt_mthd": row.get("HH_ELCT_CTRT_MTHD"),
        "clng_mng_form": row.get("CLNG_MNG_FORM"),
        "bdar": _to_decimal(row.get("BDAR")),
        "prk_cntom": _to_int(row.get("PRK_CNTOM")),
        "se_cd": row.get("SE_CD"),
        "cmpx_aprv_day": cmpx_aprv,
        "use_yn": row.get("USE_YN"),
        "mnco_uld_yn": row.get("MNCO_ULD_YN"),

        # 좌표: 칼럼은 (lng, lat) 순으로 저장 (스키마 그대로)
        "lng": lng,
        "lat": lat,

        "cmpx_apld_day": cmpx_apld,

        # 원문 JSON
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
    """apt_cd 기준으로 마지막 값을 채택."""
    by_cd: Dict[str, dict] = {}
    for r in rows:
        v = _transform_row(r)
        cd = v.get("apt_cd", "")
        if not cd:
            continue  # PK 없으면 스킵
        by_cd[cd] = v
    return list(by_cd.values())


def _upsert_rows(session: Session, rows: Sequence[dict]) -> None:
    if not rows:
        return
    chunk = int(os.getenv("DB_UPSERT_CHUNK", "1000"))
    for part in _iter_chunks(rows, chunk):
        orig_len = len(part)
        part = _dedup_transformed(part)  # apt_cd 기준 dedup
        if not part:
            continue

        stmt = insert(AptInfo).values(part)
        # PK(apt_cd)만 제외하고 전 컬럼 업데이트
        update_map = {
            c.name: getattr(stmt.excluded, c.name)
            for c in AptInfo.__table__.columns
            if c.name != "apt_cd"
        }
        session.execute(
            stmt.on_conflict_do_update(index_elements=[AptInfo.apt_cd], set_=update_map),
            execution_options={"synchronize_session": False},
        )
        LOGGER.info(
            "aptinfo upsert chunk=%s (deduped %s rows)",
            len(part), orig_len - len(part)
        )


# ---------- main ----------
def run(service_name: str | None = None, *, api_key: str | None = None) -> None:
    key = api_key or os.getenv("SEOUL_API_KEY_APTINFO") or os.getenv("SEOUL_API_KEY")
    if not key:
        raise RuntimeError("SEOUL_API_KEY not set")

    service = service_name or os.getenv("SEOUL_APTINFO_SERVICE") or probe_service(key, SERVICE_CANDIDATES)

    commit_every = int(os.getenv("DB_COMMIT_EVERY", "1"))
    throttle = float(os.getenv("SEOUL_API_THROTTLE", "0.2"))
    resume_from = int(os.getenv("SEOUL_RESUME_PAGE", "1"))

    with SessionLocal() as session:
        t0 = time.time()
        batch_count = 0
        for page_idx, batch in enumerate(
            # fetch_pages가 start_page를 지원하지 않으면 그냥 전체 돌고 page_idx로 스킵해도 됩니다.
            fetch_pages(key, service, throttle_seconds=throttle),
            start=1,
        ):
            if page_idx < resume_from:
                if page_idx % 100 == 0:
                    LOGGER.info("skip batch %s", page_idx)
                continue

            _upsert_rows(session, batch)
            batch_count = page_idx
            if batch_count % commit_every == 0:
                session.commit()
                LOGGER.info("aptinfo batch %s committed", batch_count)

        session.commit()
        LOGGER.info("aptinfo completed: %s batches in %.1fs", batch_count, time.time() - t0)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()

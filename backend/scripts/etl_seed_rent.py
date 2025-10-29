# -*- coding: utf-8 -*-
from __future__ import annotations
"""Seed the rent table with lease payloads from the Seoul API (bulk upsert, dedup, resume, retry)."""

import argparse
import logging
import os
import time
from decimal import Decimal, InvalidOperation
from typing import Iterable, Sequence, Dict, Tuple

# (옵션) .env 있으면 읽고, 없어도 조용히 패스
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.db_connection import SessionLocal
from app.models.rent import Rent
from app.utils.normalize import (
    clean_lot_jibun,
    mwon_to_krw,
    norm_text,
    stable_bigint_id,
    yyyymmdd_to_date,
)
from app.utils.seoul_api import fetch_pages, probe_service

LOGGER = logging.getLogger(__name__)
SERVICE_CANDIDATES = ("tbLnOpendataRentV", "RealEstateRent", "tbLnOpendataJeonse")


# ---------- tiny config helpers ----------
def _env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None or str(v).strip() == "":
        return default
    try:
        return int(str(v).strip())
    except Exception:
        return default


def _env_float(name: str, default: float) -> float:
    v = os.getenv(name)
    if v is None or str(v).strip() == "":
        return default
    try:
        return float(str(v).strip())
    except Exception:
        return default


def _env_str(name: str, default: str) -> str:
    v = os.getenv(name)
    return default if v is None or str(v).strip() == "" else str(v).strip()


# ---------- helpers ----------
def _to_decimal(v: object) -> Decimal | None:
    if v in (None, "", " ", "NULL"):
        return None
    try:
        return Decimal(str(v).strip())
    except (InvalidOperation, TypeError, ValueError):
        return None


def _to_int(v: object) -> int | None:
    if v in (None, "", " "):
        return None
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        try:
            return int(Decimal(str(v)))
        except Exception:
            return None


def _lot_from(row: dict) -> str | None:
    main, sub = row.get("MNO"), row.get("SNO")
    if main in (None, "", "0"):
        return None
    lot = str(main)
    if sub not in (None, "", "0"):
        lot = f"{lot}-{sub}"
    return clean_lot_jibun(lot)


def _coords(_: dict) -> Tuple[Decimal | None, Decimal | None]:
    # 전월세 API에는 좌표 없음(추후 제공되면 여기서 파싱)
    return None, None


def _transform_row(row: dict) -> dict:
    raw = dict(row)

    contract_date = yyyymmdd_to_date(row.get("CTRT_DAY"))
    area_m2 = _to_decimal(row.get("RENT_AREA"))
    deposit_m = row.get("GRFE")
    rent_m = row.get("RTFE")

    deposit_krw = mwon_to_krw(deposit_m)  # 만원 → 원
    rent_krw = mwon_to_krw(rent_m)

    lot_key = _lot_from(row)
    lat, lng = _coords(row)

    return {
        # PK (row 기반 stable 해시)
        "id": stable_bigint_id(raw),

        # === 원본 컬럼 ===
        "rcpt_yr": _to_int(row.get("RCPT_YR")),
        "cgg_cd": row.get("CGG_CD"),
        "cgg_nm": row.get("CGG_NM"),
        "stdg_cd": row.get("STDG_CD"),
        "stdg_nm": row.get("STDG_NM"),
        "lotno_se": row.get("LOTNO_SE"),
        "lotno_se_nm": row.get("LOTNO_SE_NM"),
        "mno": row.get("MNO"),
        "sno": row.get("SNO"),
        "flr": _to_int(row.get("FLR")),
        "ctrt_day": row.get("CTRT_DAY"),
        "rent_se": row.get("RENT_SE"),
        "rent_area": area_m2,          # ㎡ (원본 단위 유지)
        "grfe_mwon": _to_int(deposit_m),
        "rtfe_mwon": _to_int(rent_m),
        "bldg_nm": row.get("BLDG_NM"),
        "arch_yr": _to_int(row.get("ARCH_YR")),
        "bldg_usg": row.get("BLDG_USG"),
        "ctrt_prd": row.get("CTRT_PRD"),
        "new_updt_yn": row.get("NEW_UPDT_YN"),
        "ctrt_updt_use_yn": row.get("CTRT_UPDT_USE_YN"),
        "bfr_grfe_mwon": _to_int(row.get("BFR_GRFE")),
        "bfr_rtfe_mwon": _to_int(row.get("BFR_RTFE")),

        # === 파생 ===
        "contract_date": contract_date,
        "area_m2": area_m2,            # Decimal(㎡)
        "deposit_krw": deposit_krw,    # 원
        "rent_krw": rent_krw,          # 원
        "lot_key": lot_key,
        "gu_key": norm_text(row.get("CGG_NM")),
        "dong_key": norm_text(row.get("STDG_NM")),
        "name_key": norm_text(row.get("BLDG_NM")),
        "lat": lat,
        "lng": lng,

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


def _upsert_rows(session: Session, rows: Sequence[dict], chunk: int) -> None:
    if not rows:
        return
    for part in _iter_chunks(rows, chunk):
        orig_len = len(part)
        part = _dedup_transformed(part)
        if not part:
            continue

        stmt = insert(Rent).values(part)

        # created_at 보존, updated_at 은 now() 로 갱신
        update_map = {
            c.name: getattr(stmt.excluded, c.name)
            for c in Rent.__table__.columns
            if c.name not in ("id", "created_at", "updated_at")
        }
        update_map["updated_at"] = func.now()

        session.execute(
            stmt.on_conflict_do_update(
                index_elements=[Rent.id],
                set_=update_map,
            ),
            execution_options={"synchronize_session": False},
        )
        LOGGER.info(
            "rent upsert chunk=%s (deduped %s rows)",
            len(part), orig_len - len(part)
        )


# ---------- main ----------
def run(
    service_name: str | None = None,
    *,
    api_key: str | None = None,
    resume_from: int | None = None,
    chunk: int | None = None,
    commit_every: int | None = None,
    throttle: float | None = None,
) -> None:
    # === 키/서비스 ===
    key = api_key or _env_str("SEOUL_API_KEY_RENT", _env_str("SEOUL_API_KEY", ""))
    if not key:
        raise RuntimeError("SEOUL_API_KEY not set")

    service = service_name or _env_str("SEOUL_RENT_SERVICE", "") or probe_service(key, SERVICE_CANDIDATES)

    # === 튜닝값(우선순위: 인자 > ENV > 기본) ===
    eff_chunk = chunk if chunk is not None else _env_int("DB_UPSERT_CHUNK", 5000)
    eff_commit_every = commit_every if commit_every is not None else _env_int("DB_COMMIT_EVERY", 10)
    eff_throttle = throttle if throttle is not None else _env_float("SEOUL_API_THROTTLE", 0.02)
    eff_resume = resume_from if resume_from is not None else _env_int("SEOUL_RESUME_PAGE", 1)

    LOGGER.info(
        "settings -> chunk=%s, commit_every=%s, throttle=%.3f, resume_from=%s, service=%s",
        eff_chunk, eff_commit_every, eff_throttle, eff_resume, service,
    )

    with SessionLocal() as session:
        t0 = time.time()
        last_page = eff_resume - 1

        for page_idx, batch in enumerate(
            fetch_pages(key, service, throttle_seconds=eff_throttle, start_page=eff_resume),
            start=eff_resume,
        ):
            _upsert_rows(session, batch, eff_chunk)
            last_page = page_idx

            if last_page % eff_commit_every == 0:
                session.commit()
                LOGGER.info("rent batch %s committed", last_page)

            if last_page % 100 == 0:
                LOGGER.info("progress: batch %s done", last_page)

        session.commit()
        LOGGER.info(
            "rent completed: last_batch=%s, elapsed=%.1fs",
            last_page, time.time() - t0
        )


def _build_cli() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Seed rent table from Seoul OpenAPI")
    p.add_argument("--resume", type=int, default=None, help="start page index to resume from (1-based)")
    p.add_argument("--chunk", type=int, default=None, help="upsert chunk size (rows per DB write)")
    p.add_argument("--commit-every", type=int, default=None, help="commit every N batches")
    p.add_argument("--throttle", type=float, default=None, help="API call throttle seconds between pages")
    p.add_argument("--service", type=str, default=None, help="override service name")
    return p


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    args = _build_cli().parse_args()
    run(
        service_name=args.service,
        resume_from=args.resume,
        chunk=args.chunk,
        commit_every=args.commit_every,
        throttle=args.throttle,
    )

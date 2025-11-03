# backend/app/api/bounds_db.py
from __future__ import annotations

from fastapi import APIRouter, Query
from typing import Literal, Sequence, Set
from sqlalchemy import text
from app.db.db_connection import SessionLocal

router = APIRouter(prefix="/api/bounds", tags=["bounds"])

Level = Literal["sido", "sgg", "emd"]


# ---------- helpers ----------
def _cols_for(table: str) -> Set[str]:
    """해당 테이블의 실제 컬럼명을 lowercase set으로 반환."""
    sql = text("""
        SELECT lower(column_name) AS c
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = :t
    """)
    with SessionLocal() as s:
        rows = s.execute(sql, {"t": table.split(".")[-1]}).fetchall()
    return {r[0] for r in rows}


def _first_present(cols: Set[str], candidates: Sequence[str]) -> str | None:
    for c in candidates:
        if c.lower() in cols:
            return c
    return None


def _base_table(level: Level) -> str:
    # 시/도 테이블이 비어있으므로 sido도 sgg 테이블을 사용해 dissolve
    return "public.adm_sgg" if level in ("sido", "sgg") else "public.adm_emd"


def _code_expr(level: Level, cols: Set[str]) -> str:
    if level == "emd":
        return _first_present(cols, ["emd_cd", "emdcode", "code", "id"]) or "id"
    # sgg/sido
    return _first_present(cols, ["sig_cd", "sgg_cd", "sggcode", "code", "id"]) or "id"


def _name_expr(level: Level, cols: Set[str]) -> str:
    """
    실제 존재하는 이름 컬럼만 사용해서 COALESCE 구성.
    테이블마다 이름 컬럼이 제각각이므로 후보를 넉넉히.
    """
    # 공통 후보(있으면 우선)
    common = [ "name", "adm_nm", "ar_name" ]

    if level == "emd":
        cand = ["emd_kor_nm", "emd_nm", "emd_name", "emd_han_nm"] + common
    else:  # sgg/sido
        cand = ["sgg_nm", "sig_kor_nm", "sgg_name", "az_sid_nm", "sido_nm"] + common

    present = [c for c in cand if c.lower() in cols]
    if not present:
        return "'미상'"
    if len(present) == 1:
        return present[0]
    return f"COALESCE({', '.join(present)})"


def _tolerance(level: Level, zoom: float) -> float:
    """
    간단한 경험치 톨러런스. (줌 낮을수록 약간 키움)
    """
    base = 0.0003 if level == "emd" else (0.0008 if level == "sgg" else 0.0015)
    # 줌이 12보다 작으면 조금 더 단순화
    if zoom <= 11.5:
        base *= 1.5
    return base


# ---------- endpoint ----------
@router.get("")
def bounds_db(
    level: Level = Query(..., description="sido|sgg|emd"),
    west: float = Query(...),
    south: float = Query(...),
    east: float = Query(...),
    north: float = Query(...),
    zoom: float = Query(12.0),
):
    tbl = _base_table(level)
    cols = _cols_for(tbl)

    code = _code_expr(level, cols)
    name_expr = _name_expr(level, cols)
    tol = _tolerance(level, zoom)

    # 공통: 현재 뷰포트 bbox
    bbox_cte = """
      WITH bbox AS (
        SELECT ST_MakeEnvelope(:west,:south,:east,:north, 4326) AS g
      )
    """

    if level == "sido":
        # adm_sgg를 시/도 단위로 dissolve
        # 코드: sgg코드의 좌측 2자리(시/도) 사용
        # 이름: 테이블에 시/도 이름 컬럼이 있으면 사용, 없으면 시/군/구 이름 중 하나를 대표값으로 COALESCE
        sgg_code = _code_expr("sgg", cols)
        sido_code = f"LEFT({sgg_code}, 2)"  # e.g. 11(서울), 28(인천) 등

        # 시/도 이름이 없으면 name_expr에서 대표값을 가져오되, group 내 대표 하나 사용
        sql = text(f"""
        {bbox_cte}
        SELECT jsonb_build_object(
          'type', 'FeatureCollection',
          'features', COALESCE(jsonb_agg(
            jsonb_build_object(
              'type', 'Feature',
              'properties', jsonb_build_object(
                'code', {sido_code},
                'name', MAX({name_expr})
              ),
              'geometry',
                ST_AsGeoJSON(
                  ST_SimplifyPreserveTopology(
                    ST_Union(                         -- dissolve
                      ST_Intersection(t.geom, b.g)
                    ),
                    :tol
                  )
                )::jsonb
            )
          ), '[]'::jsonb)
        ) AS fc
        FROM {tbl} t
        CROSS JOIN bbox b
        WHERE t.geom && b.g
        GROUP BY {sido_code}
        """)
    else:
        # sgg/emd 일반 경계
        sql = text(f"""
        {bbox_cte}
        SELECT jsonb_build_object(
          'type', 'FeatureCollection',
          'features', COALESCE(jsonb_agg(
            jsonb_build_object(
              'type', 'Feature',
              'properties', jsonb_build_object('code', {code}, 'name', {name_expr}),
              'geometry',
                ST_AsGeoJSON(
                  ST_SimplifyPreserveTopology(
                    ST_Intersection(t.geom, b.g),
                    :tol
                  )
                )::jsonb
            )
          ), '[]'::jsonb)
        ) AS fc
        FROM {tbl} t
        CROSS JOIN bbox b
        WHERE t.geom && b.g
          AND NOT ST_IsEmpty(ST_Intersection(t.geom, b.g))
        """)

    with SessionLocal() as s:
        fc = s.execute(sql, {
            "west": west, "south": south, "east": east, "north": north,
            "tol": tol,
        }).scalar()

    # 실패/빈 결과 방어
    return fc or {"type": "FeatureCollection", "features": []}

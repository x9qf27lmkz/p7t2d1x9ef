# -*- coding: utf-8 -*-
from __future__ import annotations

import os, json, math
from typing import List, Tuple

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"), override=False)

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.db_connection import SessionLocal
from app.utils.normalize import stable_bigint_id

BATCH = int(os.getenv("BACKFILL_BATCH", "2000"))
TABLE = "public.cloud_aptinfo"
IDX   = "cloud_aptinfo_id_uidx"
PK    = "cloud_aptinfo_pkey"

def _ensure_id_column(s: Session):
    # aptinfo는 기존에 id 없었다고 했으니 방어적 생성
    s.execute(text(f"""
        ALTER TABLE {TABLE} ADD COLUMN IF NOT EXISTS id BIGINT;
    """))

def _rows_to_update_count(s: Session) -> int:
    r = s.execute(text(f"SELECT count(*) FROM {TABLE} WHERE id IS NULL")).scalar()
    return int(r or 0)

def _fetch_ctid_raw_batch(s: Session, last_ctid_txt: str | None, limit: int) -> List[Tuple[str, dict]]:
    # ctid 텍스트 비교로 페이징 (소량 테이블 + 단발 작업에 충분)
    if last_ctid_txt:
        q = text(f"""
            SELECT t.ctid::text AS ctid_txt, t.raw
            FROM {TABLE} t
            WHERE t.id IS NULL AND t.ctid::text > :last
            ORDER BY t.ctid
            LIMIT :lim
        """)
        rows = s.execute(q, {"last": last_ctid_txt, "lim": limit}).all()
    else:
        q = text(f"""
            SELECT t.ctid::text AS ctid_txt, t.raw
            FROM {TABLE} t
            WHERE t.id IS NULL
            ORDER BY t.ctid
            LIMIT :lim
        """)
        rows = s.execute(q, {"lim": limit}).all()
    return [(r[0], r[1]) for r in rows]

def _update_ids_by_ctid(s: Session, ctids: List[str], ids: List[int]):
    # 바인드 배열은 CAST(:param AS type[])로!
    s.execute(text(f"""
        WITH d AS (
          SELECT a.ctid_txt, b.id
          FROM unnest(CAST(:ctids AS text[]))  WITH ORDINALITY AS a(ctid_txt, ord)
          JOIN unnest(CAST(:ids   AS bigint[])) WITH ORDINALITY AS b(id,      ord)
            USING (ord)
        )
        UPDATE {TABLE} t
        SET id = d.id
        FROM d
        WHERE t.ctid = d.ctid_txt::tid
    """), {"ctids": ctids, "ids": ids})

def _create_unique_index_concurrently_autocommit():
    # 트랜잭션을 **사용하지 않는** 별도 커넥션에서 실행해야 함
    with SessionLocal() as s2:
        engine = s2.get_bind()
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text(f"""
            CREATE UNIQUE INDEX IF NOT EXISTS {IDX}
            ON {TABLE}(id);
        """))
        # CONCURRENTLY가 꼭 필요하면 위를 이렇게:
        # conn.execute(text(f"CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS {IDX} ON {TABLE}(id)"))

def _attach_pk_using_index(s: Session):
    # PK 없으면 인덱스를 PK로 연결
    s.execute(text(f"""
        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = '{PK}'
          ) THEN
            ALTER TABLE {TABLE}
              ADD CONSTRAINT {PK} PRIMARY KEY USING INDEX {IDX};
          END IF;
        END$$;
    """))

def main():
    with SessionLocal() as s:
        # 1) id 컬럼 보장
        _ensure_id_column(s)
        s.commit()

        # 2) 백필 대상 수집
        total = _rows_to_update_count(s)
        pages = math.ceil(total / BATCH) if total else 0
        print(f"[aptinfo] backfill start: {total} rows, {pages} pages, batch={BATCH}")

        last_ctid = None
        done = 0
        page = 0
        while done < total:
            rows = _fetch_ctid_raw_batch(s, last_ctid, BATCH)
            if not rows:
                break
            ctids = [ctid for (ctid, _raw) in rows]
            ids   = [stable_bigint_id(raw) for (_ctid, raw) in rows]

            _update_ids_by_ctid(s, ctids, ids)
            s.commit()

            done += len(rows)
            page += 1
            last_ctid = ctids[-1]
            print(f"[aptinfo] committed page {page}/{pages or 1} (rows={len(rows)})")

        # 3) (세션 트랜잭션이 **없어야**) 유니크 인덱스 생성
        #    방금까지의 세션은 트랜잭션이 끝난 상태여야 함
        s.commit()

    # 3-1) 별도 커넥션 + AUTOCOMMIT로 인덱스 생성
    _create_unique_index_concurrently_autocommit()

    # 4) 인덱스를 PK로 연결 (일반 세션 내에서 가능)
    with SessionLocal() as s:
        _attach_pk_using_index(s)
        s.commit()

    print("✅ aptinfo id backfill + PK done.")

if __name__ == "__main__":
    main()

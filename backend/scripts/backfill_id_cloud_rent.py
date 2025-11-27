# -*- coding: utf-8 -*-
from __future__ import annotations
import os
from dotenv import load_dotenv
from sqlalchemy import text
from app.db.db_connection import SessionLocal
from app.utils.normalize import stable_bigint_id

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"), override=False)

BATCH = int(os.getenv("BACKFILL_BATCH", "5000"))  # 속도 올림

SQL_PICK = text("""
    SELECT ctid::text AS ctid_txt, raw
    FROM public.cloud_rent
    WHERE id_hash IS NULL
    LIMIT :lim
""")

SQL_UPDATE = text("""
    WITH d AS (
      SELECT a.ctid_txt, b.id
      FROM unnest(:ctids) WITH ORDINALITY AS a(ctid_txt, ord)
      JOIN unnest(:ids)   WITH ORDINALITY AS b(id,       ord) USING (ord)
    )
    UPDATE public.cloud_rent t
    SET id_hash = d.id
    FROM d
    WHERE t.ctid = d.ctid_txt::tid
""")

def main():
    with SessionLocal() as s:
        # 진짜 남은 대상 수(시점마다 달라지므로 매 라운드 재계산)
        remain = s.execute(text("SELECT COUNT(*) FROM public.cloud_rent WHERE id_hash IS NULL")).scalar_one()
        if not remain:
            print("[rent] nothing to backfill"); return
        print(f"[rent] backfill start: remain={remain}, batch={BATCH}")

        rounds = 0
        while True:
            rows = s.execute(SQL_PICK, {"lim": BATCH}).fetchall()
            if not rows:
                break  # 남은 대상 없음 → 종료

            ctids = [r.ctid_txt for r in rows]
            ids   = [stable_bigint_id(dict(r.raw)) for r in rows]

            # 방어: 비어있으면 수행 안 함 (unnest('{}') 방지)
            if ctids and ids:
                s.execute(SQL_UPDATE, {"ctids": ctids, "ids": ids})
                s.commit()

            rounds += 1
            if rounds % 20 == 0:
                left = s.execute(text("SELECT COUNT(*) FROM public.cloud_rent WHERE id_hash IS NULL")).scalar_one()
                print(f"[rent] committed rounds={rounds}, last_rows={len(rows)}, remain={left}")

        left = s.execute(text("SELECT COUNT(*) FROM public.cloud_rent WHERE id_hash IS NULL")).scalar_one()
        print(f"✅ rent id_hash backfill done. remain={left}")

if __name__ == "__main__":
    main()

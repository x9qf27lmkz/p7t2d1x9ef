# alembic/versions/xxxx_create_view_v_apartment_price_84.py
from alembic import op

# revision identifiers, used by Alembic.
revision = "b55e8c65ec72"          # ← 파일에 생성된 값 유지
down_revision = "070701caed66"     # ← 파일에 생성된 값 유지
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE OR REPLACE VIEW v_apartment_price_84 AS
    -- 0) trades에 apartment_id가 없어도, 이름 + 주소 포함 매칭으로 apartments.id 매핑
    WITH tmap AS (
      SELECT
        t.*,
        a.id AS apartment_id
      FROM seoul_trades t
      LEFT JOIN apartments a
        ON a.name = t.complex
       AND (
            -- 주소(도로명/지번) 안에 구/동이 포함되면 매칭 (a.gu/a.dong 없어도 동작)
            (
              a.addr_road IS NOT NULL
              AND a.addr_road ILIKE ('%' || t.gu   || '%')
              AND (t.dong IS NULL OR a.addr_road ILIKE ('%' || t.dong || '%'))
            )
            OR
            (
              a.addr_jibun IS NOT NULL
              AND a.addr_jibun ILIKE ('%' || t.gu   || '%')
              AND (t.dong IS NULL OR a.addr_jibun ILIKE ('%' || t.dong || '%'))
            )
           )
    ),

    -- 1) 최근 12개월 거래만 대상으로 기본 집계 소스
    base AS (
      SELECT
        tm.apartment_id,
        tm.contract_date,
        (tm.price_krw / NULLIF(tm.area_m2 / 3.305785, 0))::numeric AS py_price
      FROM tmap tm
      WHERE tm.apartment_id IS NOT NULL
        AND tm.contract_date >= (CURRENT_DATE - INTERVAL '12 months')
    ),

    -- 2) 단지별 가용 윈도우(3→6→12개월) 선택
    win AS (
      SELECT
        apartment_id,
        CASE
          WHEN COUNT(*) FILTER (WHERE contract_date >= CURRENT_DATE - INTERVAL '3 months') > 0 THEN '3m'
          WHEN COUNT(*) FILTER (WHERE contract_date >= CURRENT_DATE - INTERVAL '6 months') > 0 THEN '6m'
          ELSE '12m'
        END AS picked_window
      FROM base
      GROUP BY apartment_id
    ),

    -- 3) 선택 윈도우의 거래만 추출
    picked AS (
      SELECT b.*
      FROM base b
      JOIN win w USING (apartment_id)
      WHERE (w.picked_window = '3m'  AND b.contract_date >= CURRENT_DATE - INTERVAL '3 months')
         OR (w.picked_window = '6m'  AND b.contract_date >= CURRENT_DATE - INTERVAL '6 months')
         OR (w.picked_window = '12m' AND b.contract_date >= CURRENT_DATE - INTERVAL '12 months')
    ),

    -- 4) 중앙값 평당가/건수 집계
    agg AS (
      SELECT
        apartment_id,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY py_price) AS median_py_price,
        COUNT(*) AS deal_count
      FROM picked
      GROUP BY apartment_id
    )

    -- 5) apartments 기준 LEFT JOIN → 거래 없어도 마커 표시
    SELECT
      a.id   AS apartment_id,
      a.name AS apartment_name,
      a.addr_road,
      a.addr_jibun,
      a.lat, a.lng,
      ag.median_py_price,
      CASE
        WHEN ag.median_py_price IS NOT NULL
          THEN ROUND(ag.median_py_price * (84 / 3.305785))::bigint
        ELSE NULL
      END AS price_84,
      COALESCE(ag.deal_count, 0) AS deal_count
    FROM apartments a
    LEFT JOIN agg ag ON ag.apartment_id = a.id;
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_apartment_price_84;")

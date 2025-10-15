from alembic import op

# revision identifiers, used by Alembic.
revision = "62a3c3f9492d"        # ← 파일 상단 생성된 값 유지
down_revision = "0dd7de0ba45c"   # ← init 리비전 ID(이미 자동 세팅되어 있을 것)
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE OR REPLACE VIEW v_apartment_price_84 AS
    -- trades에 apartment_id가 없어도, 단지명+구(+동)으로 apartments 매핑
    WITH tmap AS (
      SELECT
        t.*,
        a.id AS apartment_id
      FROM seoul_trades t
      LEFT JOIN apartments a
        ON a.name = t.complex
       AND a.gu   = t.gu
       AND (t.dong IS NULL OR a.dong = t.dong)
    ),

    -- 최근 12개월 거래만 가져와 평당가 계산
    base AS (
      SELECT
        tm.apartment_id,
        tm.contract_date,
        (tm.price_krw / NULLIF(tm.area_m2 / 3.305785, 0))::numeric AS py_price
      FROM tmap tm
      WHERE tm.apartment_id IS NOT NULL
        AND tm.contract_date >= (CURRENT_DATE - INTERVAL '12 months')
    ),

    -- 단지별로 3→6→12개월 중 사용 가능한 윈도우 선택
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

    picked AS (
      SELECT b.*
      FROM base b
      JOIN win w USING (apartment_id)
      WHERE (w.picked_window = '3m'  AND b.contract_date >= CURRENT_DATE - INTERVAL '3 months')
         OR (w.picked_window = '6m'  AND b.contract_date >= CURRENT_DATE - INTERVAL '6 months')
         OR (w.picked_window = '12m' AND b.contract_date >= CURRENT_DATE - INTERVAL '12 months')
    ),

    agg AS (
      SELECT
        apartment_id,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY py_price) AS median_py_price,
        COUNT(*) AS deal_count
      FROM picked
      GROUP BY apartment_id
    )

    -- apartments를 기준으로 LEFT JOIN → 거래 없어도 마커에 노출
    SELECT
      a.id   AS apartment_id,
      a.name AS apartment_name,
      a.gu, a.dong, a.lat, a.lng,
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

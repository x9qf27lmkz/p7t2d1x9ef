"""recreate rent with full api columns"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# 리비전 식별자는 Alembic가 자동 생성한 값 그대로 두세요.
revision = "<자동생성값>"
down_revision = None  # 기존 의존관계 없다면 None, 다른 리비전에 붙일거면 거기 값

def upgrade():
    # 안전하게 기존 rent 있으면 날리고 새로 만든다 (개발환경 가정)
    conn = op.get_bind()
    conn.execute(sa.text('DROP TABLE IF EXISTS "rent" CASCADE'))

    op.create_table(
        "rent",
        # --- PK ---
        sa.Column("id", sa.BigInteger(), primary_key=True),

        # ===== API 원본 컬럼 =====
        sa.Column("rcpt_yr", sa.Integer(), nullable=True),           # 접수연도
        sa.Column("cgg_cd", sa.Text(), nullable=True),               # 자치구코드
        sa.Column("cgg_nm", sa.Text(), nullable=True),               # 자치구명
        sa.Column("stdg_cd", sa.Text(), nullable=True),              # 법정동코드
        sa.Column("stdg_nm", sa.Text(), nullable=True),              # 법정동명
        sa.Column("lotno_se", sa.Text(), nullable=True),             # 지번구분
        sa.Column("lotno_se_nm", sa.Text(), nullable=True),          # 지번구분명
        sa.Column("mno", sa.Text(), nullable=True),                  # 본번
        sa.Column("sno", sa.Text(), nullable=True),                  # 부번
        sa.Column("flr", sa.Integer(), nullable=True),               # 층
        sa.Column("ctrt_day", sa.Text(), nullable=True),             # 계약일(원문 YYYYMMDD)
        sa.Column("rent_se", sa.Text(), nullable=True),              # 전월세 구분
        sa.Column("rent_area", sa.Numeric(10, 2), nullable=True),    # 임대면적(㎡) 원문
        sa.Column("grfe_mwon", sa.Integer(), nullable=True),         # 보증금(만원) 원문
        sa.Column("rtfe_mwon", sa.Integer(), nullable=True),         # 임대료(만원) 원문
        sa.Column("bldg_nm", sa.Text(), nullable=True),              # 건물명
        sa.Column("arch_yr", sa.Integer(), nullable=True),           # 건축년도
        sa.Column("bldg_usg", sa.Text(), nullable=True),             # 건물용도
        sa.Column("ctrt_prd", sa.Text(), nullable=True),             # 계약기간(원문)
        sa.Column("new_updt_yn", sa.Text(), nullable=True),          # 신규/갱신 여부
        sa.Column("ctrt_updt_use_yn", sa.Text(), nullable=True),     # 갱신권 사용여부
        sa.Column("bfr_grfe_mwon", sa.Integer(), nullable=True),     # 종전 보증금(만원)
        sa.Column("bfr_rtfe_mwon", sa.Integer(), nullable=True),     # 종전 임대료(만원)

        # ===== 파생 컬럼 =====
        sa.Column("contract_date", sa.Date(), nullable=True),        # 파싱된 날짜
        sa.Column("area_m2", sa.Numeric(10, 2), nullable=True),      # = rent_area
        sa.Column("deposit_krw", sa.BigInteger(), nullable=True),    # 보증금(원)
        sa.Column("rent_krw", sa.BigInteger(), nullable=True),       # 임대료(원)
        sa.Column("lot_key", sa.Text(), nullable=True),              # "본번-부번"
        sa.Column("gu_key", sa.Text(), nullable=True),
        sa.Column("dong_key", sa.Text(), nullable=True),
        sa.Column("name_key", sa.Text(), nullable=True),
        sa.Column("lat", sa.Numeric(10, 7), nullable=True),
        sa.Column("lng", sa.Numeric(10, 7), nullable=True),

        # 원본 JSON
        sa.Column("raw", postgresql.JSONB(astext_type=sa.Text()), nullable=False),

        # 감사용 타임스탬프
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # 인덱스 (조회용)
    op.create_index(op.f("ix_rent_contract_date"), "rent", ["contract_date"], unique=False)
    op.create_index(op.f("ix_rent_cgg_nm"), "rent", ["cgg_nm"], unique=False)
    op.create_index(op.f("ix_rent_stdg_nm"), "rent", ["stdg_nm"], unique=False)
    op.create_index(op.f("ix_rent_lot_key"), "rent", ["lot_key"], unique=False)
    op.create_index(op.f("ix_rent_name_key"), "rent", ["name_key"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_rent_name_key"), table_name="rent")
    op.drop_index(op.f("ix_rent_lot_key"), table_name="rent")
    op.drop_index(op.f("ix_rent_stdg_nm"), table_name="rent")
    op.drop_index(op.f("ix_rent_cgg_nm"), table_name="rent")
    op.drop_index(op.f("ix_rent_contract_date"), table_name="rent")
    op.drop_table("rent")

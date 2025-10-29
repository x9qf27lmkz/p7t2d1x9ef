"""SQLAlchemy model for apartment sale transactions (full API columns + derived keys)."""
from __future__ import annotations

from sqlalchemy import BigInteger, Column, Date, DateTime, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.db.orm_registry import Base


class Sale(Base):
    __tablename__ = "sale"

    # PK
    id = Column(BigInteger, primary_key=True)

    # 원본 JSON
    raw = Column(JSONB, nullable=False)

    # === API 원본 컬럼 ===
    rcpt_yr = Column(Integer, nullable=True)           # 접수연도
    cgg_cd = Column(Integer, nullable=True)            # 자치구코드
    cgg_nm = Column(Text, nullable=True)               # 자치구명
    stdg_cd = Column(Integer, nullable=True)           # 법정동코드
    stdg_nm = Column(Text, nullable=True)              # 법정동명
    lotno_se = Column(Integer, nullable=True)          # 지번구분
    lotno_se_nm = Column(Text, nullable=True)          # 지번구분명
    mno = Column(Text, nullable=True)                  # 본번 (문자 보존)
    sno = Column(Text, nullable=True)                  # 부번 (문자 보존)
    bldg_nm = Column(Text, nullable=True)              # 건물명
    ctrt_day = Column(Date, nullable=True, index=True) # 계약일(Date 변환)
    thing_amt = Column(BigInteger, nullable=True)      # 물건금액(원)
    arch_area = Column(Numeric(12, 3), nullable=True)  # 건물면적(㎡)
    land_area = Column(Numeric(12, 3), nullable=True)  # 토지면적(㎡)
    flr = Column(Text, nullable=True)                  # 층 (정수/특수표기 혼재 → TEXT)
    rght_se = Column(Text, nullable=True)              # 권리구분
    rtrcn_day = Column(Text, nullable=True)            # 취소일(원문 그대로)
    arch_yr = Column(Integer, nullable=True)           # 건축년도
    bldg_usg = Column(Text, nullable=True)             # 건물용도
    dclr_se = Column(Text, nullable=True)              # 신고구분
    opbiz_restagnt_sgg_nm = Column(Text, nullable=True)# 개업공인중개사 시군구명

    # === 파생 키/좌표 ===
    gu_key = Column(Text, nullable=True, index=True)
    dong_key = Column(Text, nullable=True, index=True)
    name_key = Column(Text, nullable=True, index=True)
    lot_key = Column(Text, nullable=True, index=True)
    lat = Column(Numeric(10, 7), nullable=True)
    lng = Column(Numeric(10, 7), nullable=True)

    # 메타
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

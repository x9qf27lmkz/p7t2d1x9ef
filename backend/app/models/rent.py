# app/models/rent.py
"""SQLAlchemy model for apartment rent/lease transactions (wide schema)."""
from __future__ import annotations

from sqlalchemy import BigInteger, Column, Date, DateTime, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.db.orm_registry import Base


class Rent(Base):
    __tablename__ = "rent"

    # 안정적 해시 PK (원본 row 전체 해시)
    id = Column(BigInteger, primary_key=True)

    # ---- API 원본 필드 (tbLnOpendataRentV) ----
    rcpt_yr = Column(Integer, index=True)        # 접수연도
    cgg_cd = Column(Text)                        # 자치구코드
    cgg_nm = Column(Text, index=True)            # 자치구명
    stdg_cd = Column(Text)                       # 법정동코드
    stdg_nm = Column(Text, index=True)           # 법정동명
    lotno_se = Column(Text)                      # 지번구분
    lotno_se_nm = Column(Text)                   # 지번구분명
    # 본/부번은 선행 0 보존을 위해 Text
    mno = Column(Text)                           # 본번 (예: "0490")
    sno = Column(Text)                           # 부번 (예: "0000")
    flr = Column(Integer)                        # 층
    ctrt_day = Column(Text)                      # 계약일 yyyymmdd (원본 문자열)
    rent_se = Column(Text)                       # 전월세 구분
    rent_area = Column(Numeric(10, 2))           # 임대면적(㎡)
    grfe_mwon = Column(Integer)                  # 보증금(만원)
    rtfe_mwon = Column(Integer)                  # 임대료(만원)
    bldg_nm = Column(Text, index=True)           # 건물명
    arch_yr = Column(Integer)                    # 건축년도
    bldg_usg = Column(Text)                      # 건물용도
    ctrt_prd = Column(Text)                      # 계약기간 (문자열 "YY.MM~YY.MM")
    new_updt_yn = Column(Text)                   # 신규/갱신 여부
    ctrt_updt_use_yn = Column(Text)              # 계약갱신권 사용
    bfr_grfe_mwon = Column(Integer)              # 종전 보증금(만원)
    bfr_rtfe_mwon = Column(Integer)              # 종전 임대료(만원)

    # ---- 파생/정규화 필드 ----
    contract_date = Column(Date, index=True)     # 파싱된 날짜
    area_m2 = Column(Numeric(10, 2))             # 면적(동일 단위 재보관)
    deposit_krw = Column(BigInteger)             # 보증금(원)
    rent_krw = Column(BigInteger)                # 임대료(원)
    lot_key = Column(Text, index=True)           # "mno-sno" 정규화 (선행 0 제거)
    gu_key = Column(Text, index=True)            # 검색용 소문자/공백정리
    dong_key = Column(Text, index=True)
    name_key = Column(Text, index=True)

    # 이 API는 좌표 제공 안함 -> NULL
    lat = Column(Numeric(10, 7))
    lng = Column(Numeric(10, 7))

    # ---- 원본 JSON ----
    raw = Column(JSONB, nullable=False)

    # ---- 감사 ----
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

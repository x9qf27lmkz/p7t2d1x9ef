"""SQLAlchemy model for Seoul OpenAptInfo (column-per-field, natural PK)."""
from __future__ import annotations

from sqlalchemy import (
    Column,
    Text,
    Integer,
    Date,
    DateTime,
    Numeric,
    BigInteger,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.db.orm_registry import Base


class AptInfo(Base):
    __tablename__ = "aptinfo"

    # 자연키
    apt_cd = Column(Text, primary_key=True)  # APT_CD

    # ====== 원본 매핑 컬럼 ======
    sn = Column(Integer)                                   # SN
    apt_nm = Column(Text, index=True)                      # APT_NM
    cmpx_clsf = Column(Text)                               # CMPX_CLSF

    apt_stdg_addr = Column(Text)                           # APT_STDG_ADDR (법정동 주소)
    apt_rdn_addr = Column(Text)                            # APT_RDN_ADDR (도로명 주소)

    ctpv_addr = Column(Text)                               # CTPV_ADDR (시/도)
    sgg_addr = Column(Text)                                # SGG_ADDR (시군구)
    emd_addr = Column(Text)                                # EMD_ADDR (읍면동)
    daddr = Column(Text)                                   # DADDR (지번/나머지)
    rdn_addr = Column(Text)                                # RDN_ADDR (도로명)
    road_daddr = Column(Text)                              # ROAD_DADDR (도로 상세)

    telno = Column(Text)                                   # TELNO
    fxno = Column(Text)                                    # FXNO
    apt_cmpx = Column(Text)                                # APT_CMPX (소개)
    apt_atch_file = Column(Text)                           # APT_ATCH_FILE

    hh_type = Column(Text)                                 # HH_TYPE (분양/임대)
    mng_mthd = Column(Text)                                # MNG_MTHD (관리방식)
    road_type = Column(Text)                               # ROAD_TYPE (복도 유형)
    mn_mthd = Column(Text)                                 # MN_MTHD (난방방식)

    whol_dong_cnt = Column(Integer)                        # WHOL_DONG_CNT (전체 동수)
    tnohsh = Column(Integer)                               # TNOHSH (전체 세대수)

    bldr = Column(Text)                                    # BLDR (시공)
    dvlr = Column(Text)                                    # DVLR (시행)

    # 날짜/수치
    use_aprv_ymd = Column(Date)                            # USE_APRV_YMD (사용승인일)
    gfa = Column(Numeric(14, 2))                           # GFA (연면적)
    rsdt_xuar = Column(Numeric(14, 2))                     # RSDT_XUAR (주거전용)
    mnco_levy_area = Column(Numeric(14, 2))                # MNCO_LEVY_AREA
    xuar_hh_stts60 = Column(Numeric(14, 2))                # XUAR_HH_STTS60
    xuar_hh_stts85 = Column(Numeric(14, 2))                # XUAR_HH_STTS85
    xuar_hh_stts135 = Column(Numeric(14, 2))               # XUAR_HH_STTS135
    xuar_hh_stts136 = Column(Numeric(14, 2))               # XUAR_HH_STTS136

    hmpg = Column(Text)                                    # HMPG
    reg_ymd = Column(Date)                                 # REG_YMD
    mdfcn_ymd = Column(Date)                               # MDFCN_YMD

    epis_mng_no = Column(Text)                             # EPIS_MNG_NO
    eps_mng_form = Column(Text)                            # EPS_MNG_FORM
    hh_elct_ctrt_mthd = Column(Text)                       # HH_ELCT_CTRT_MTHD
    clng_mng_form = Column(Text)                           # CLNG_MNG_FORM
    bdar = Column(Numeric(14, 2))                          # BDAR (건축면적)
    prk_cntom = Column(Integer)                            # PRK_CNTOM (주차대수)
    se_cd = Column(Text)                                   # SE_CD (의무/임의 등)

    cmpx_aprv_day = Column(Date)                           # CMPX_APRV_DAY (단지 승인일)
    use_yn = Column(Text)                                  # USE_YN
    mnco_uld_yn = Column(Text)                             # MNCO_ULD_YN

    lng = Column(Numeric(10, 7))                           # XCRD -> lng
    lat = Column(Numeric(10, 7))                           # YCRD -> lat
    cmpx_apld_day = Column(Date)                           # CMPX_APLD_DAY (단지 신청일)

    # ====== 검색/조인용 보조 키 ======
    gu_key = Column(Text, index=True)                      # norm(SGG_ADDR)
    dong_key = Column(Text, index=True)                    # norm(EMD_ADDR)
    name_key = Column(Text, index=True)                    # norm(APT_NM)
    lot_key = Column(Text, index=True)                     # clean(APT_STDG_ADDR)

    # ====== 보조 ======
    raw = Column(JSONB, nullable=False)                    # 원본 보관(디버깅/감사)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

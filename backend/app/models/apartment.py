# app/models/apartment.py
from sqlalchemy import Column, Integer, Text, Numeric, UniqueConstraint, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_mixin
from app.db.base import Base

class Apartment(Base):
    __tablename__ = "apartments"

    id = Column(Integer, primary_key=True)
    source = Column(Text, nullable=False, default="SEOUL_APT")
    source_id = Column(Text, nullable=False)              # APT_CD
    name = Column(Text, nullable=False)                   # APT_NM
    addr_road = Column(Text)                              # DORO_ADDR
    addr_jibun = Column(Text)                             # JIBUN_ADDR
    gu = Column(Text)                                     # SIGG_ADDR / GU
    dong = Column(Text)                                   # DONG
    year_approved = Column(Integer)                       # CMPLX_APPRV_DAY(yyyy)
    xcrd = Column(Numeric)                                # 원본 X
    ycrd = Column(Numeric)                                # 원본 Y
    lat = Column(Numeric)                                 # WGS84 위도
    lng = Column(Numeric)                                 # WGS84 경도
    use_yn = Column(Text)                                 # USE_YN
    created_at = Column(Text, server_default=func.now())
    updated_at = Column(Text, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("source", "source_id", name="uq_apartments_source_sourceid"),
        Index("idx_apartments_gu_dong", "gu", "dong"),
        Index("idx_apartments_lat_lng", "lat", "lng"),
    )

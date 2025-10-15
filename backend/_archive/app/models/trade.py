from sqlalchemy import Column, Integer, String, Float, Date, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base import Base

class SeoulTrade(Base):
    __tablename__ = "seoul_trades"
    id = Column(Integer, primary_key=True, autoincrement=True)
    gu = Column(String(20), index=True, nullable=False)
    dong = Column(String(30), index=True, nullable=True)
    complex = Column(String(80), index=True, nullable=True)
    lot_number = Column(String(20), nullable=True)
    building_use = Column(String(20), nullable=True)
    area_m2 = Column(Float, index=True, nullable=True)
    price_krw = Column(Integer, index=True, nullable=True)
    contract_date = Column(Date, index=True, nullable=True)
    build_year = Column(Integer, nullable=True)
    floor = Column(Integer, nullable=True)
    report_year = Column(Integer, index=True, nullable=True)
    declare_type = Column(String(20), nullable=True)
    opr_sgg = Column(String(30), nullable=True)
    lat = Column(Float, index=True, nullable=True)
    lng = Column(Float, index=True, nullable=True)
    raw_json = Column(JSONB, nullable=False)

    __table_args__ = (
        UniqueConstraint("gu","dong","complex","lot_number","area_m2","contract_date","price_krw",
                         name="uq_trade_identity"),
        Index("ix_trade_geo", "lat", "lng"),
        Index("ix_trade_period", "gu", "contract_date"),
    )

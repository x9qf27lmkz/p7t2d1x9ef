"""SQLAlchemy model for apartment rent/lease transactions."""
from __future__ import annotations

from sqlalchemy import BigInteger, Column, Date, DateTime, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.db.base import Base


class Rent(Base):
    """Apartment rent contract sourced from the Seoul open API."""

    __tablename__ = "rent"

    id = Column(BigInteger, primary_key=True)
    raw = Column(JSONB, nullable=False)
    contract_date = Column(Date, nullable=True, index=True)
    deposit_krw = Column(BigInteger, nullable=True)
    rent_krw = Column(BigInteger, nullable=True)
    area_m2 = Column(Numeric(10, 2), nullable=True)
    gu_key = Column(Text, nullable=True, index=True)
    dong_key = Column(Text, nullable=True, index=True)
    name_key = Column(Text, nullable=True, index=True)
    lot_key = Column(Text, nullable=True, index=True)
    lat = Column(Numeric(10, 7), nullable=True)
    lng = Column(Numeric(10, 7), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


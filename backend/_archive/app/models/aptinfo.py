"""SQLAlchemy model for core apartment metadata."""
from __future__ import annotations

from sqlalchemy import BigInteger, Column, Date, DateTime, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.db.base import Base


class AptInfo(Base):
    """Basic apartment information record."""

    __tablename__ = "aptinfo"

    id = Column(BigInteger, primary_key=True)
    raw = Column(JSONB, nullable=False)
    approval_date = Column(Date, nullable=True)
    year_approved = Column(Integer, nullable=True)
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


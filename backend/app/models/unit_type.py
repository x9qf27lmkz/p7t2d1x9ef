# app/models/unit_type.py

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base

class UnitType(Base):
    __tablename__ = "unit_types"

    id = Column(Integer, primary_key=True, index=True)
    apartment_id = Column(Integer, ForeignKey("apartments.id", ondelete="CASCADE"))
    unit_type = Column(String, nullable=False)  # ex: "24평", "32평"
    household_count = Column(Integer, default=0)
    avg_rent_price = Column(Integer, nullable=True)  # ex: 110000000
    avg_sale_price = Column(Integer, nullable=True)  # ex: 680000000

    apartment = relationship("Apartment", back_populates="unit_types")

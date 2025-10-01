from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.orm import relationship
from app.db.database import Base

class Apartment(Base):
    __tablename__ = "apartments"

    id = Column(Integer, primary_key=True, index=True)
    apt_code = Column(String, unique=True, index=True)
    apt_name = Column(String)
    total_households = Column(Integer)
    size_range = Column(String)

    old_address = Column(String)       # 구주소
    new_address = Column(String)       # 신주소

    x = Column(Float)                  # 경도
    y = Column(Float)                  # 위도

    # ✅ 관계 정의
    sale_records = relationship("SaleRecord", back_populates="apartment")
    rental_contracts = relationship("RentalContract", back_populates="apartment")
    household_status = relationship("HouseholdStatus", back_populates="apartment")
    unit_types = relationship("UnitType", back_populates="apartment", cascade="all, delete-orphan")  # ✅ 추가

    def __repr__(self):
        return f"<Apartment(name={self.apt_name}, code={self.apt_code}, households={self.total_households})>"

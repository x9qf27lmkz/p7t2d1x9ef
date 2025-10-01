from sqlalchemy import Column, Integer, Float, Boolean, Date, ForeignKey, String
from sqlalchemy.orm import relationship
from app.db.database import Base

class HouseholdStatus(Base):
    __tablename__ = "household_status"

    id = Column(Integer, primary_key=True, index=True)
    apt_code = Column(String, index=True)    # 아파트 코드 (고유 식별자)
    size = Column(Float, index=True)         # 평형 단위
    is_owner_residing = Column(Boolean)      # 실거주 여부
    is_rented = Column(Boolean)              # 임대 여부
    is_vacant = Column(Boolean)              # 공실 여부
    status_date = Column(Date)               # 상태 확인 날짜
    apartment_id = Column(Integer, ForeignKey('apartments.id'))  # 외래키

    apartment = relationship("Apartment", back_populates="household_status")

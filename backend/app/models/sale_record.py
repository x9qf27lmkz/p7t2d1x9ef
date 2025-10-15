from sqlalchemy import Column, Integer, Float, Date, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base

class SaleRecord(Base):
    __tablename__ = "sale_record"

    id = Column(Integer, primary_key=True, index=True)
    apt_code = Column(String, index=True)
    size = Column(Float)
    sale_price = Column(Integer)
    sale_date = Column(Date)
    apartment_id = Column(Integer, ForeignKey('apartments.id'))

    apartment = relationship("Apartment", back_populates="sale_records")

from sqlalchemy import Column, Integer, Float, Boolean, Date, ForeignKey, String
from sqlalchemy.orm import relationship
from app.db.database import Base

class RentalContract(Base):
    __tablename__ = "rental_contract"

    id = Column(Integer, primary_key=True, index=True)
    apt_code = Column(String, index=True)
    size = Column(Float)
    rent_price = Column(Integer)
    contract_date = Column(Date)
    apartment_id = Column(Integer, ForeignKey('apartments.id'))

    apartment = relationship("Apartment", back_populates="rental_contracts")

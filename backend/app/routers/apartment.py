from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.models.apartment import Apartment
from app.schemas.apartment import ApartmentSchema

router = APIRouter(
    prefix="/apartments",
    tags=["apartments"]
)

@router.get("/", response_model=List[ApartmentSchema])
def get_all_apartments(db: Session = Depends(get_db)):
    """
    모든 아파트 정보를 반환합니다.
    """
    apartments = db.query(Apartment).all()
    return apartments

@router.get("/{apt_code}", response_model=ApartmentSchema)
def get_apartment_by_code(apt_code: str, db: Session = Depends(get_db)):
    """
    apt_code로 특정 아파트 정보를 조회합니다.
    """
    apartment = db.query(Apartment).filter(Apartment.apt_code == apt_code).first()
    if apartment is None:
        raise HTTPException(status_code=404, detail="Apartment not found")
    return apartment

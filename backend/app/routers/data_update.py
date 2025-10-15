from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services import apartment_service, data_service

router = APIRouter()

# 데이터 리셋 및 새 데이터 삽입
@router.post("/reset_apartment_data")
def reset_apartment_data(apt_code: str, db: Session = Depends(get_db)):
    return apartment_service.reset_apartment_data(db, apt_code)

@router.post("/insert_new_data")
def insert_new_data(household_data: list, sale_data: list, rental_data: list, db: Session = Depends(get_db)):
    return data_service.insert_new_data(db, household_data, sale_data, rental_data)

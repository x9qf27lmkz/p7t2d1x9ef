from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from app.db.database import get_db
from app.models.apartment import Apartment as ApartmentModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Pydantic 모델
class Apartment(BaseModel):
    id: int
    apt_name: str
    x: float
    y: float

    class Config:
        orm_mode = True

# ✅ DB에서 아파트 목록 조회
@app.get("/apartments/", response_model=List[Apartment])
def get_apartments(db: Session = Depends(get_db)):
    return db.query(ApartmentModel).filter(
        ApartmentModel.x.isnot(None), ApartmentModel.y.isnot(None)
    ).all()

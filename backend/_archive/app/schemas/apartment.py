# app/schemas/apartment.py

from pydantic import BaseModel
from typing import Optional

class ApartmentSchema(BaseModel):
    id: int
    apt_code: str
    apt_name: str
    total_households: Optional[int]
    size_range: Optional[str]
    old_address: Optional[str]
    new_address: Optional[str]
    x: Optional[float]
    y: Optional[float]

    # ✅ 아래 필드들 추가해야 함
    gu: Optional[str]
    dong: Optional[str]
    year_approved: Optional[int]
    lat: Optional[float]
    lng: Optional[float]

    class Config:
        orm_mode = True

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

    class Config:
        orm_mode = True

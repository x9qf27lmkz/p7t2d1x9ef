# app/seed.py
from app.db.database import SessionLocal
from app.models import Apartment, HouseholdStatus, SaleRecord, RentalContract
from datetime import datetime, timedelta
import random

def create_dummy_apartments():
    db = SessionLocal()
    apartments = [
        {"apt_code": "노원102", "apt_name": "노원힐스 1단지", "total_households": 150, "old_address": "강남구 123-45", "new_address": "강남구 신주소1"},
        {"apt_code": "송파102", "apt_name": "송파힐스 2단지", "total_households": 200, "old_address": "송파구 543-21", "new_address": "송파구 신주소2"},
        {"apt_code": "마포103", "apt_name": "마포힐스 3단지", "total_households": 120, "old_address": "마포구 678-90", "new_address": "마포구 신주소3"},
    ]

    print("🏢 아파트 데이터 삽입 중...")
    for apt in apartments:
        db_apartment = Apartment(**apt)
        db.add(db_apartment)
    db.commit()

    print("🏠 세대 상태 데이터 삽입 중...")
    for apt in apartments:
        for _ in range(apt['total_households']):
            status = HouseholdStatus(
                apt_code=apt['apt_code'],
                size=random.choice([25.0, 40.0, 50.0]),
                is_owner_residing=random.choice([True, False]),
                is_rented=random.choice([True, False]),
                is_vacant=random.choice([True, False]),
                status_date=datetime.now() - timedelta(days=random.randint(0, 365))
            )
            db.add(status)
        db.commit()

    print("💵 매매 이력 데이터 삽입 중...")
    for apt in apartments:
        for _ in range(5):
            sale_record = SaleRecord(
                apt_code=apt['apt_code'],
                size=random.choice([25.0, 40.0, 50.0]),
                sale_price=random.randint(20000, 80000),
                sale_date=datetime.now() - timedelta(days=random.randint(365, 1000))
            )
            db.add(sale_record)
        db.commit()

    print("📑 임대차 계약 데이터 삽입 중...")
    for apt in apartments:
        for _ in range(5):
            rental_contract = RentalContract(
                apt_code=apt['apt_code'],
                size=random.choice([25.0, 40.0, 50.0]),
                rent_price=random.randint(500, 1500),
                contract_date=datetime.now() - timedelta(days=random.randint(365, 1000))
            )
            db.add(rental_contract)
        db.commit()

    print("✅ 더미 데이터 삽입 완료!")

if __name__ == "__main__":
    create_dummy_apartments()

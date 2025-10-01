# scripts/insert_unit_types_from_csv.py

import csv
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.apartment import Apartment
from app.models.unit_type import UnitType

def insert_unit_types_from_csv(csv_path: str):
    db: Session = SessionLocal()

    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            apt_code = row["apt_code"]
            apartment = db.query(Apartment).filter_by(apt_code=apt_code).first()
            if not apartment:
                print(f"❌ Apartment with apt_code '{apt_code}' not found. Skipping.")
                continue

            unit_type = UnitType(
                apartment_id=apartment.id,
                unit_type=row["unit_type"],
                household_count=int(row["household_count"]),
                avg_rent_price=int(row["avg_rent_price"]) if row["avg_rent_price"] else None,
                avg_sale_price=int(row["avg_sale_price"]) if row["avg_sale_price"] else None
            )
            db.add(unit_type)

    db.commit()
    db.close()
    print("✅ Unit types inserted successfully.")

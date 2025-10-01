# backend/app/scripts/update_apartment_coordinates.py

import csv
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.apartment import Apartment

CSV_FILE = "app/data/노원구_전체아파트단지_주소좌표_완성.csv"

def update_coordinates():
    db: Session = SessionLocal()
    updated = 0

    with open(CSV_FILE, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            apt_code = row['단지코드']
            x = float(row['x']) if row['x'] else None
            y = float(row['y']) if row['y'] else None

            apartment = db.query(Apartment).filter(Apartment.apt_code == apt_code).first()
            if apartment:
                apartment.x = x
                apartment.y = y
                updated += 1
                print(f"✔ {apt_code} updated → x: {x}, y: {y}")

        db.commit()
        db.close()
        print(f"\n총 {updated}개 아파트 좌표 업데이트 완료.")

if __name__ == "__main__":
    update_coordinates()
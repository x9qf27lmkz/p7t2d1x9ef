import csv
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.apartment import Apartment

CSV_FILE = "app/data/노원구_전체아파트단지_주소좌표_완성.csv"

def insert_apartments():
    db: Session = SessionLocal()
    inserted = 0

    with open(CSV_FILE, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            apt_code = row['단지코드'].strip()
            apt_name = row['\ufeff단지명'].strip()
            old_address = row.get('구주소') or ''
            new_address = row.get('신주소') or ''
            x = float(row['x']) if row['x'] else None
            y = float(row['y']) if row['y'] else None

            apartment = Apartment(
                apt_code=apt_code,
                apt_name=apt_name,
                total_households=0,
                size_range='',
                old_address=old_address,
                new_address=new_address,
                x=x,
                y=y,
            )
            db.add(apartment)
            inserted += 1

        db.commit()
        db.close()
        print(f"\n총 {inserted}개 아파트 단지 삽입 완료.")

if __name__ == "__main__":
    insert_apartments()

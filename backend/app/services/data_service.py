from sqlalchemy.orm import Session
from app.models import HouseholdStatus, SaleRecord, RentalContract

# 새 데이터 삽입 (리셋된 후)
def insert_new_data(db: Session, household_data: list, sale_data: list, rental_data: list):
    # 세대 상태 삽입
    for data in household_data:
        new_status = HouseholdStatus(**data)
        db.add(new_status)

    # 매매 이력 삽입
    for data in sale_data:
        new_sale = SaleRecord(**data)
        db.add(new_sale)

    # 임대차 이력 삽입
    for data in rental_data:
        new_rental = RentalContract(**data)
        db.add(new_rental)

    db.commit()
    return {"message": "New data inserted successfully"}

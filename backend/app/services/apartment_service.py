from sqlalchemy.orm import Session
from app.models import Apartment, HouseholdStatus, SaleRecord, RentalContract

# 단지별 세대 상태, 매매 이력, 임대차 이력 모두 리셋
def reset_apartment_data(db: Session, apt_code: str):
    # 기존 세대 상태, 매매 이력, 임대차 이력 삭제
    db.query(HouseholdStatus).filter(HouseholdStatus.apt_code == apt_code).delete()
    db.query(SaleRecord).filter(SaleRecord.apt_code == apt_code).delete()
    db.query(RentalContract).filter(RentalContract.apt_code == apt_code).delete()
    
    db.commit()
    return {"message": "Data reset successfully"}

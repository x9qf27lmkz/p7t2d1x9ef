# app/db/base.py
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# ⚠️ 모든 모델을 여기서 import 해야 Base.metadata에 등록됩니다.
#from app.models.apartment import Apartment  # noqa: F401
#from app.models.trade import SeoulTrade     # noqa: F401
# 필요하면 아래도 추가
# from app.models.rental_contract import RentalContract  # noqa: F401
# from app.models.household_status import HouseholdStatus  # noqa: F401
# from app.models.unit_type import UnitType  # noqa: F401
# from app.models.sale_record import SaleRecord  # noqa: F401

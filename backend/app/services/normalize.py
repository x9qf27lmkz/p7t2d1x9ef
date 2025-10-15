# app/services/normalize.py
from datetime import date

def normalize_row(r: dict) -> dict:
    # lot_number
    mno, sno = r.get("MNO"), r.get("SNO")
    lot_number = f"{mno}-{sno}" if mno and sno else (mno or sno or None)

    # price
    price_manwon = r.get("THING_AMT")
    price_krw = int(price_manwon) * 10000 if price_manwon and str(price_manwon).isdigit() else None

    # contract date
    ctrt = r.get("CTRT_DAY")
    contract_date = None
    if ctrt and len(ctrt) == 8 and ctrt.isdigit():
        contract_date = date(int(ctrt[:4]), int(ctrt[4:6]), int(ctrt[6:]))

    # floats/ints
    def to_float(x):
        try: return float(x) if x not in (None, "") else None
        except: return None
    def to_int(x):
        try: return int(x) if str(x).isdigit() else None
        except: return None

    return {
        "gu": r.get("CGG_NM"),
        "dong": r.get("STDG_NM"),
        "complex": r.get("BLDG_NM"),
        "lot_number": lot_number,
        "building_use": r.get("BLDG_USG"),
        "area_m2": to_float(r.get("ARCH_AREA")),
        "price_krw": price_krw,
        "contract_date": contract_date,
        "build_year": to_int(r.get("ARCH_YR")),
        "floor": to_int(r.get("FLOOR")),
        "report_year": to_int(r.get("RCPT_YR")),
        "declare_type": r.get("DCLR_SE"),
        "opr_sgg": r.get("OPRZ_RESTAGNT_SGG_NM"),
        "lat": None, "lng": None,
        "raw_json": r,
    }

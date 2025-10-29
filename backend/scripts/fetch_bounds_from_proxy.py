# backend/scripts/fetch_bounds_from_proxy.py
import json, math, time, os
import requests

API = os.getenv("API_BASE", "http://127.0.0.1:8000")  # 우리 FastAPI
OUT_DIR = os.getenv("OUT_DIR", "./data")
os.makedirs(OUT_DIR, exist_ok=True)

# 서울 대략 BBOX (EPSG:4326)
SEOUL = dict(west=126.72, south=37.41, east=127.20, north=37.73)

# 타일 크기 (deg) – 너무 작게 잡으면 콜 수 많아짐
STEP = 0.08

def tiles(b):
    y = b["south"]
    while y < b["north"]:
        x = b["west"]
        y2 = min(b["north"], y + STEP)
        while x < b["east"]:
            x2 = min(b["east"], x + STEP)
            yield dict(west=x, south=y, east=x2, north=y2)
            x = x2
        y = y2

def fetch_bbox(level, bbox):
    url = f"{API}/api/vworld/bounds"
    params = dict(level=level, **bbox)
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    fc = r.json().get("response", {}).get("result", {}).get("featureCollection", {})
    return fc.get("features", [])

def collect(level, code_key, name_key):
    seen = {}  # code -> feature(최신)
    for i, b in enumerate(tiles(SEOUL), 1):
        feats = fetch_bbox(level, b)
        for f in feats:
            props = f.get("properties", {})
            code = str(props.get(code_key, "")).strip()
            name = str(props.get(name_key, "")).strip()
            geom = f.get("geometry")
            if not code or not geom:
                continue
            # 같은 코드가 여러 번 올 수 있으니 마지막 것만 보관 (union은 DB에서)
            seen[code] = {"type": "Feature", "properties": {code_key: code, "name": name}, "geometry": geom}
        if i % 5 == 0:
            print(f"[{level}] tiles fetched: {i}")
        time.sleep(0.1)  # 너무 세게 두드리지 않게
    return {"type":"FeatureCollection","features": list(seen.values())}

def main():
    # 구(SGG) – VWorld 속성 키: sig_cd, sig_kor_nm (프록시 그대로 전달됨)
    sgg = collect("sigg", code_key="sig_cd", name_key="sig_kor_nm")
    with open(os.path.join(OUT_DIR, "seoul_sgg.geojson"), "w", encoding="utf-8") as f:
        json.dump(sgg, f, ensure_ascii=False)

    # 동(EMD) – 속성 키: emd_cd, emd_kor_nm
    emd = collect("emd", code_key="emd_cd", name_key="emd_kor_nm")
    with open(os.path.join(OUT_DIR, "seoul_emd.geojson"), "w", encoding="utf-8") as f:
        json.dump(emd, f, ensure_ascii=False)

    print("DONE → ./data/seoul_sgg.geojson, ./data/seoul_emd.geojson")

if __name__ == "__main__":
    main()

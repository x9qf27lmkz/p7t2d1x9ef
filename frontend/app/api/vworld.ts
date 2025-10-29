import axios from 'axios';

const KEY   = process.env.EXPO_PUBLIC_VWORLD_KEY!;
const DOMAIN= process.env.EXPO_PUBLIC_VWORLD_DOMAIN!; // http://127.0.0.1:8000 등

type DataId = 'LT_C_ADSIDO_INFO' | 'LT_C_ADSIGG_INFO' | 'LT_C_ADEMD_INFO';

export async function fetchAdminGeojson(data: DataId, bbox: [number, number, number, number]) {
  const [minx, miny, maxx, maxy] = bbox;
  const base = 'https://api.vworld.kr/req/data';

  const params = new URLSearchParams({
    service: 'data',
    request: 'GetFeature',
    data,
    key: KEY,
    domain: DOMAIN,         // 🔑 중요
    format: 'json',
    size: '1000',           // 최대 1000
    crs: 'EPSG:4326',
    geomFilter: `BOX(${minx},${miny},${maxx},${maxy})`,
  });

  const { data: res } = await axios.get(base + '?' + params.toString());
  if (res?.response?.status === 'OK') {
    // vworld 구조 → GeoJSON FeatureCollection로 변환
    const feats = res.response.result?.featureCollection?.features ?? [];
    return {
      type: 'FeatureCollection',
      features: feats.map((f: any) => ({
        type: 'Feature',
        geometry: f.geometry,
        properties: f.properties,
      })),
    };
  }
  const err = res?.response?.error;
  throw new Error(err ? `${err.code}: ${err.text}` : 'vworld error');
}

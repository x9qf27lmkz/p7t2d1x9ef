// src/services/api.js
import axios from "axios";

const baseURL =
  process.env.EXPO_PUBLIC_API_BASE?.replace(/\/+$/, "") || "http://localhost:8000";

const api = axios.create({
  baseURL,
  timeout: 8000,
});

export default api;

// 백엔드가 /map/markers (쿼리파라미터: minX, minY, maxX, maxY, zoom, mode) 를 제공한다는 가정
export async function fetchMarkers(params = {}) {
  const {
    minX = 126.76, minY = 37.40,
    maxX = 127.18, maxY = 37.70,
    zoom = 13, mode = "sale",
  } = params;

  const { data } = await api.get("/map/markers", {
    params: { minX, minY, maxX, maxY, zoom, mode },
  });

  // 백엔드 응답 형태에 맞춰 안전하게 꺼내기
  // - 새 라우터(map.py)는 { markers: [...] }일 확률 큼
  // - 예전 뷰(map_markers.py)는 { items: [...] }였음
  return data?.markers ?? data?.items ?? [];
}

// src/services/api.js
export async function getComplexSummary(gu) {
  const resp = await fetch(`/api/complex/summary?gu=${encodeURIComponent(gu)}`);
  if (!resp.ok) throw new Error(`API ${resp.status}`);
  return resp.json();
}

// (기존 fetchMarkers 등 다른 함수가 있어도 그대로 두세요)

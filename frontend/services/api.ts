// services/api.ts
import axios from 'axios';

const baseURL =
  process.env.EXPO_PUBLIC_API_BASE?.replace(/\/+$/, '') ?? 'http://localhost:8000';

const api = axios.create({
  baseURL,
  timeout: 8000,
});

export interface FetchMarkersParams {
  minX?: number;
  minY?: number;
  maxX?: number;
  maxY?: number;
  zoom?: number;
  mode?: string;
}

export interface MarkerSummary {
  id?: number;
  name?: string;
  gu?: string;
  dong?: string;
  lat?: number | null;
  lng?: number | null;
  price_84?: number | null;
  deals?: number | null;
}

export default api;

export async function fetchMarkers(
  params: FetchMarkersParams = {},
): Promise<MarkerSummary[]> {
  const {
    minX = 126.76,
    minY = 37.4,
    maxX = 127.18,
    maxY = 37.7,
    zoom = 13,
    mode = 'sale',
  } = params;

  const response = await api.get<{ markers?: MarkerSummary[]; items?: MarkerSummary[] }>(
    '/map/markers',
    {
      params: { minX, minY, maxX, maxY, zoom, mode },
    },
  );

  const { markers, items } = response.data ?? {};
  return markers ?? items ?? [];
}

export async function getComplexSummary(gu: string): Promise<unknown> {
  const resp = await fetch(`/api/complex/summary?gu=${encodeURIComponent(gu)}`);
  if (!resp.ok) {
    throw new Error(`API ${resp.status}`);
  }
  return resp.json();
}

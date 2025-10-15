// src/components/MapMarkers.jsx
import { useEffect, useRef, useState, useMemo } from "react";
import useKakaoLoader from "../hooks/usekakaoloader";
import { getComplexSummary } from "../services/api";

const DEFAULT_GU = "노원구";

function formatKRW(n) {
  if (n == null) return "미입력";
  try {
    // 억/만 간단 표기 (예: 26.8억)
    const billion = 100_000_000;
    if (n >= billion) {
      const v = (n / billion);
      return `${v.toFixed(v >= 10 ? 0 : 1)}억`;
    }
    return n.toLocaleString("ko-KR");
  } catch {
    return String(n);
  }
}

export default function MapMarkers() {
  const { error, withKakao } = useKakaoLoader(); // clusterer 로더 포함
  const [gu] = useState(DEFAULT_GU);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  const mapRef = useRef(null);
  const map = useRef(null);
  const clusterer = useRef(null);
  const overlaysRef = useRef([]);   // kakao.maps.CustomOverlay[]
  const markersRef = useRef([]);    // kakao.maps.Marker[]

  // 데이터 로딩
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const data = await getComplexSummary(gu);
        if (!alive) return;
        // 기대 스키마: { name, lat, lng, pyeong:32, salePrice, jeonsePrice }
        setRows(Array.isArray(data) ? data.filter(d => Number.isFinite(d.lat) && Number.isFinite(d.lng)) : []);
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, [gu]);

  // 오버레이 DOM 생성 함수 (kakao SDK 외부에서 미리 만들기)
  const makeOverlayContent = useMemo(() => (row) => {
    const el = document.createElement("div");
    el.style.cssText = [
      "background:#fff",
      "border:1px solid #e5e7eb",
      "border-radius:10px",
      "padding:8px 10px",
      "box-shadow:0 6px 20px rgba(0,0,0,0.12)",
      "font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif",
      "font-size:12px",
      "color:#111827",
      "white-space:nowrap",
      "transform:translateY(-4px)"
    ].join(";");

    const title = document.createElement("div");
    title.style.cssText = "font-weight:600;margin-bottom:4px;";
    title.textContent = row.name || "단지명 미상";

    const sale = document.createElement("div");
    sale.textContent = `매매가(32평): ${formatKRW(row.salePrice)}`;

    const jeonse = document.createElement("div");
    jeonse.textContent = `전세가(32평): ${formatKRW(row.jeonsePrice)}`;

    el.appendChild(title);
    el.appendChild(sale);
    el.appendChild(jeonse);
    return el;
  }, []);

  // 지도/마커/오버레이 생성
  useEffect(() => {
    if (!mapRef.current || rows.length === 0) return;

    let cleanupFn = () => {};
    withKakao((kakao) => {
      // 지도 생성
      const center = new kakao.maps.LatLng(37.5665, 126.9780);
      map.current = new kakao.maps.Map(mapRef.current, { center, level: 7 });

      // 마커 생성
      const markers = rows.map((r) => new kakao.maps.Marker({
        position: new kakao.maps.LatLng(r.lat, r.lng)
      }));
      markersRef.current = markers;

      // 클러스터러 (마커만)
      clusterer.current = new kakao.maps.MarkerClusterer({
        map: map.current,
        averageCenter: true,
        minLevel: 6,
      });
      clusterer.current.addMarkers(markers);

      // 커스텀 오버레이 생성 (항상 보이되, 줌이 너무 낮으면 숨김)
      const overlays = rows.map((r) => {
        const pos = new kakao.maps.LatLng(r.lat, r.lng);
        return new kakao.maps.CustomOverlay({
          position: pos,
          content: makeOverlayContent(r),
          xAnchor: 0,    // 마커 오른쪽에 붙는 느낌
          yAnchor: 1.05, // 살짝 위로
          zIndex: 10,
          clickable: false,
        });
      });
      overlaysRef.current = overlays;

      // 오버레이 표시 정책 (줌 레벨별 토글)
      const applyOverlayVisibility = () => {
        const level = map.current.getLevel();
        const show = level <= 6; // 줌인(<=6) 일 때만 보이게
        overlays.forEach((ov) => ov.setMap(show ? map.current : null));
      };

      // 처음 바운드/가시화
      if (markers.length > 0) {
        const bounds = new kakao.maps.LatLngBounds();
        markers.forEach((m) => bounds.extend(m.getPosition()));
        map.current.setBounds(bounds);
      }
      applyOverlayVisibility();

      // 이벤트: 줌/드래그 후에도 규칙 반영
      kakao.maps.event.addListener(map.current, "zoom_changed", applyOverlayVisibility);
      kakao.maps.event.addListener(map.current, "idle", applyOverlayVisibility);

      // 정리
      cleanupFn = () => {
        try { overlays.forEach((ov) => ov.setMap(null)); } catch {}
        try { clusterer.current?.clear(); } catch {}
        markersRef.current = [];
        overlaysRef.current = [];
        clusterer.current = null;
        map.current = null;
      };
    });

    return cleanupFn;
  }, [withKakao, rows, makeOverlayContent]);

  if (error) return <div style={{ padding: 12 }}>SDK 오류: {String(error.message || error)}</div>;
  if (loading) return <div style={{ padding: 12 }}>불러오는 중…</div>;

  return <div ref={mapRef} style={{ width: "100%", height: "100vh" }} />;
}

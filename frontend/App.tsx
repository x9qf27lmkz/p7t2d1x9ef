// frontend/App.tsx
import React, { useMemo, useRef, useCallback, useState, useEffect } from 'react';
import {
  SafeAreaView, StatusBar, View, Alert,
  TouchableOpacity, Text, StyleSheet, Platform, TextInput, ScrollView,
} from 'react-native';
import { WebView } from 'react-native-webview';
import * as Location from 'expo-location';
import axios, { AxiosError } from 'axios';

/* ───────── CONFIG ───────── */
const VWORLD_KEY      = process.env.EXPO_PUBLIC_VWORLD_KEY ?? '';
const TOOLBAR_H       = 56;
/** 카드(툴팁) 노출 임계 줌: z17부터 카드 표시 */
const LABEL_ZOOM      = 17;
const isWeb           = Platform.OS === 'web';

/** 요약/랭킹 기능 ON/OFF (기본 OFF: 404 스팸 방지) */
const STATS_ENABLED   = process.env.EXPO_PUBLIC_STATS_ENABLED === '1';

/** 줌 UX 구간 정의 */
const Z = {
  CITY: 11,       // 서울 시 경계
  SGG_MIN: 12,    // 구 경계 12~13
  SGG_MAX: 13,
  EMD_MIN: 14,    // 동 경계 14~16
  EMD_MAX: 16,
  MARKER_MIN: 17, // 마커/카드 17+
} as const;

/* ───────── PERIOD ─────────
   백엔드 요약 테이블이 지원하는 기간(1주~36개월).
   향후 1일(1d) 추가 시 이 맵과 API만 확장하면 됨. */
const PERIODS = ["1w","1m","3m","6m","12m","24m","36m"] as const;
type Period = typeof PERIODS[number];

const PERIOD_LABEL: Record<Period,string> = {
  "1w":"1주", "1m":"1개월", "3m":"3개월", "6m":"6개월",
  "12m":"12개월", "24m":"24개월", "36m":"36개월"
};

/* ───────── UTILS ───────── */
function detectApiBase() {
  if (typeof window !== 'undefined') return `http://${window.location.hostname}:8000`;
  const envBase = process.env.EXPO_PUBLIC_API_BASE;
  return (envBase?.trim() || 'http://192.168.0.12:8000').replace(/\/+$/,'');
}
function debounce<F extends (...a:any)=>void>(fn:F, ms=250){
  let t:any; return (...a:Parameters<F>)=>{ clearTimeout(t); t=setTimeout(()=>fn(...a),ms); };
}
const fmtWon = (v:number)=> (v===0?'—':`${v.toLocaleString()}억`);
const bandForZoom = (zoom:number) =>
  zoom === Z.CITY ? 'city' :
  (zoom >= Z.SGG_MIN && zoom <= Z.SGG_MAX) ? 'sgg' :
  (zoom >= Z.EMD_MIN && zoom <= Z.EMD_MAX) ? 'emd' : null;

/* ───────── AXIOS ───────── */
const API_BASE   = detectApiBase();
const BASIC_AUTH = process.env.EXPO_PUBLIC_API_BASIC_AUTH || '';
const axiosInstance = axios.create({
  baseURL: API_BASE,
  headers: BASIC_AUTH ? {
    Authorization: 'Basic ' + (typeof btoa!=='undefined'
      ? btoa(BASIC_AUTH)
      // @ts-ignore
      : Buffer.from(BASIC_AUTH).toString('base64')),
  } : undefined,
  timeout: 30000,
});

/* ───────── WV HTML (경계 + 카드 토글) ───────── */
const buildHtml = (useVworld:boolean, vworldKey:string) => `
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"/>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin/>
  <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css"/>
  <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css"/>
  <style>
  html,body,#map{height:100%;width:100%;margin:0}
  body{background:#000}

  /* 상단 툴바 높이만큼 기본 마진 */
  .leaflet-control-container .leaflet-top{margin-top:${TOOLBAR_H}px}

  /* 🧭 줌 아이콘 겹침 방지: 지도 왼쪽 위 컨트롤 위치 조정 */
  .leaflet-top.leaflet-left{
    top: 90px !important;   /* 상단 탭/기간바 아래로 */
    left: 10px !important;
    z-index: 500;
  }

  /* Z 배지(현재 줌 레벨 표시) */
  .zoom-badge{
    background:#111;color:#fff;border-radius:10px;padding:4px 8px;
    font-size:12px;font-weight:700;box-shadow:0 2px 8px rgba(0,0,0,.25)
  }
/* 🧭 줌 아이콘 바로 아래에 줌 레벨 표시 */
  #zoomLevelBadge {
    position: absolute;
    left: 15px;           /* 줌아이콘 위치와 정렬 */
    top: 230px;           /* 줌아이콘 바로 밑으로 (필요시 ± 조정) */
    background: #111;
    color: #fff;
    border-radius: 10px;
    padding: 4px 8px;
    font-size: 12px;
    font-weight: 700;
    box-shadow: 0 2px 8px rgba(0,0,0,.25);
    z-index: 1000;
    }


  .leaflet-tooltip.apt-card-tt{
    background:transparent;border:none;box-shadow:none;z-index:9999;pointer-events:none
  }
  .cards-off .leaflet-tooltip.apt-card-tt{ display:none !important; }

  /* 아파트 정보카드 (0.7배 축소 + 중앙 정렬) */
  .apt-card{
    background:#FAF9F6;border:1px solid #E2E2E2;border-radius:12px;
    box-shadow:0 4px 14px rgba(0,0,0,.15);padding:8px 10px;min-width:160px;
    color:#1C1C1C;font-family:'Noto Serif KR','Noto Serif','Pretendard',system-ui,-apple-system,sans-serif;
    line-height:1.35; text-align:center;
    transform: scale(0.7); transform-origin: top center;
  }
  .apt-card .line{font-size:14px;font-weight:700}
  .apt-card .name{font-size:16px;font-weight:800;color:#0f172a;margin:2px 0}
  .apt-card .tx{font-size:14px;color:#6b7280;text-align:center}  /* 거래량 줄 */

  /* 클러스터 아이콘 */
  .marker-cluster div{
    background:#2f6fed;color:#fff;font-weight:800;border-radius:50%;
    width:32px;height:32px;display:flex;align-items:center;justify-content:center;
    box-shadow:0 2px 10px rgba(47,111,237,.35);font-size:12px;border:2px solid #fff
  }
  /* 구/동 라벨 박스 */
  .stat-label{
    background:#ffffff;                 /* 하얀 바탕 */
    color:#0f172a;                      /* 진한 남색 글자 */
    border:1px solid #E2E8F0;           /* 옅은 회색 테두리 */
    border-radius:12px;
    padding:6px 10px;                   /* 넓이 과다 제거 */
    min-width:140px;                    /* 정보카드 느낌 유지 */
    text-align:center;                  /* 가운데 정렬 */
    font-size:12px;
    font-weight:700;
    line-height:1.35;
    box-shadow:0 4px 14px rgba(0,0,0,.15);
    white-space:nowrap;
    pointer-events:none;
    transform: translate(-50%, -100%);  /* 좌표 위쪽에 붙이기 */
  }
  .stat-label .name {
    font-weight:800; font-size:14px; color:#0f172a;
    margin:2px 0;
  }
  .stat-label .line { color:#1f2937; opacity:.95; }

</style>

</head>
<body>
  <div id="map"></div>
  <div id="zoomLevelBadge" class="zoom-badge">Z:—</div>
  <script>
    const __post = (type, payload) => {
      try { window.parent?.postMessage(JSON.stringify({type, payload}), '*'); } catch (e) {}
      try { window.ReactNativeWebView?.postMessage(JSON.stringify({type, payload})); } catch (e) {}
    };
    window.onerror = (msg, src, line, col, err) => {
      __post('wvError', {msg:String(msg), src, line, col, stack: String(err?.stack||'')});
    };
    window.addEventListener('unhandledrejection', e => {
      __post('wvError', {msg:String(e.reason), stack:String(e.reason?.stack||'')});
    });
  </script>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin></script>
  <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
  <script>
    const center=[37.5714,126.9768];
    const map=L.map('map',{zoomControl:true, preferCanvas:true}).setView(center,12);

    const osm=L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap'});
    const vKey=${JSON.stringify(vworldKey)};
    const vBase=L.tileLayer('https://api.vworld.kr/req/wmts/1.0.0/'+vKey+'/Base/{z}/{y}/{x}.png?tileMatrixSet=EPSG:3857',{attribution:'© VWorld'});
    const vSat =L.tileLayer('https://api.vworld.kr/req/wmts/1.0.0/'+vKey+'/Satellite/{z}/{y}/{x}.jpeg?tileMatrixSet=EPSG:3857',{attribution:'© VWorld'});
    try { if(${useVworld} && vKey){ vBase.addTo(map); } else { osm.addTo(map); } }
    catch(e){ __post('wvError',{msg:'baseLayerFail', detail:String(e)}); osm.addTo(map); }

    const zoomBadge = document.getElementById('zoomLevelBadge');
    const updateZ = () => { if (zoomBadge) zoomBadge.textContent = 'Z:' + map.getZoom(); };
    map.on('zoomend moveend', updateZ); updateZ();

    const RN=window.ReactNativeWebView;
    const LABEL_ZOOM=${LABEL_ZOOM};
    let cardsEnabled=true;

    const mkCluster = () => {
      try {
        if (L.markerClusterGroup) {
          return L.markerClusterGroup({
            chunkedLoading:true,maxClusterRadius:60,spiderfyOnMaxZoom:true,disableClusteringAtZoom:LABEL_ZOOM,
            iconCreateFunction:c=>L.divIcon({html:'<div>'+c.getChildCount()+'</div>',className:'marker-cluster',iconSize:L.point(36,36)})
          }).addTo(map);
        }
      } catch(e){}
      __post('wvError',{msg:'clusterPluginMissing'});
      return L.featureGroup().addTo(map);
    };
    const cluster = mkCluster();

    /* ====== 통계 라벨 레이어 (구/동) ====== */
    const labelsPane = map.createPane('labels'); labelsPane.style.zIndex=460; labelsPane.style.pointerEvents='none';
    const statsLayer = L.featureGroup({ pane:'labels' }).addTo(map);
    function clearStats(){ try{ statsLayer.clearLayers(); }catch(e){} }
    function showStats(list){
      clearStats();
      (list||[]).forEach(it=>{
        if(!Number.isFinite(it.lat)||!Number.isFinite(it.lng)) return;
        // 숫자 포맷 유틸 (억 단위 / 천단위 콤마)
        const money = (v)=> {
          const n = Number(v ?? 0);
          if (!Number.isFinite(n)) return "—";
          return n.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
        };
        const saleTx = Number(it.sale_tx ?? 0);
        const rentTx = Number(it.rent_tx ?? 0);

        const html =
          "<div class='stat-label'>"
          +   "<div class='line'>매매가 " + money(it.sale_med) + "억</div>"
          +   "<div class='line'>매매량 " + saleTx.toLocaleString() + "건</div>"
          +   "<div class='name'>" + (it.name || '') + "</div>"
          +   "<div class='line'>전세가 " + money(it.rent_med) + "억</div>"
          +   "<div class='line'>전세량 " + rentTx.toLocaleString() + "건</div>"
          + "</div>";
        const icon = L.divIcon({className:'', html, iconAnchor:[0,0]});
        L.marker([it.lat,it.lng], {icon, interactive:false}).addTo(statsLayer);
      });
    }

    const icon=L.icon({iconUrl:"data:image/svg+xml;utf8,"+
      "<svg xmlns='http://www.w3.org/2000/svg' width='56' height='56' viewBox='0 0 64 64'>"+
      "<rect x='10' y='46' width='44' height='8' rx='2' fill='rgb(96,165,250)'/>"+
      "<rect x='10' y='24' width='12' height='22' rx='2' fill='rgb(59,130,246)'/>"+
      "<rect x='26' y='18' width='12' height='28' rx='2' fill='rgb(59,130,246)'/>"+
      "<rect x='42' y='24' width='12' height='22' rx='2' fill='rgb(59,130,246)'/>"+
      "</svg>", iconSize:[56,56],iconAnchor:[28,56]});

    const tooltipEls = [];
    function updateCardsVisibility(){
      const show = (map.getZoom() >= LABEL_ZOOM) && cardsEnabled;
      tooltipEls.forEach(el => { if(el) el.style.display = show ? '' : 'none'; });
    }
    function setCardsEnabled(v){
      cardsEnabled = !!v;
      document.documentElement.classList.toggle('cards-off', !cardsEnabled);
      updateCardsVisibility();
    }

    function money(v){
        const n = Number(v ?? 0);
        if (!Number.isFinite(n)) return '0.0억';
        return n.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + '억';
    }
    function addPlaces(list){
      try { cluster.clearLayers?.(); } catch(e){}
      tooltipEls.length = 0;
      (list||[]).forEach(p=>{
        if(!Number.isFinite(p.lat)||!Number.isFinite(p.lng)) return;
        const m=L.marker([p.lat,p.lng],{icon});
        const html =
          "<div class='apt-card'>"
          +   "<div class='line'>매매가 " + money(p.sale_price) + "억</div>"
          +   "<div class='line'>매매량 " + Number(p.sale_tx||0).toLocaleString() + "건</div>"
          +   "<div class='name'>" + (p.title??p.name??'—') + "</div>"
          +   "<div class='line'>전세가 " + money(p.rent_price) + "억</div>"
          +   "<div class='line'>전세량 " + Number(p.rent_tx||0).toLocaleString() + "건</div>"
          + "</div>";
        const tt=m.bindTooltip(html,{permanent:true,direction:'bottom',className:'leaflet-tooltip apt-card-tt'}).getTooltip();
        const el=tt?.getElement(); if(el) tooltipEls.push(el);
        m.on('click',()=>RN?.postMessage?.(JSON.stringify({type:'markerClick',payload:p})));
        cluster.addLayer(m);
      });
      updateCardsVisibility();
    }

    map.on('zoomend', updateCardsVisibility);

    /* ====== 경계 레이어 ====== */
    const boundsPane = map.createPane('bounds'); boundsPane.style.zIndex=450; boundsPane.style.pointerEvents='none';
    let sidoLayer=null, sggLayer=null, emdLayer=null;
    function clearBounds(){ [sidoLayer,sggLayer,emdLayer].forEach(l=>{ if(l){ try{ map.removeLayer(l);}catch(e){} }}); sidoLayer=sggLayer=emdLayer=null; }
    function showSido(fc){ if(sidoLayer) map.removeLayer(sidoLayer);  sidoLayer=L.geoJSON(fc,{pane:'bounds',interactive:false,style:()=>({color:'#64748b',weight:2,dashArray:'3,6',fill:false})}).addTo(map); }
    function showSgg(fc){ if(sggLayer) map.removeLayer(sggLayer);  sggLayer=L.geoJSON(fc,{pane:'bounds',interactive:false,style:()=>({color:'#1f6feb',weight:2.5,dashArray:'4,4',fill:false})}).addTo(map); }
    function showEmd(fc){ if(emdLayer) map.removeLayer(emdLayer);  emdLayer=L.geoJSON(fc,{pane:'bounds',interactive:false,style:()=>({color:'#16a34a',weight:1.5,fillColor:'#16a34a',fillOpacity:0.08})}).addTo(map); }

    function postBounds(){
      const b=map.getBounds();
      const payload={type:'bounds',payload:{north:b.getNorth(),south:b.getSouth(),east:b.getEast(),west:b.getWest(),zoom:map.getZoom()}};
      try { window.ReactNativeWebView?.postMessage(JSON.stringify(payload)); } catch (e) {}
      try { window.parent?.postMessage(JSON.stringify(payload),'*'); } catch (e) {}
    }
    map.on('moveend zoomend',postBounds);

    function switchBase(mode){
      [osm,vBase,vSat].forEach(l=>{ try{ map.removeLayer(l);}catch(e){} });
      try{
        if(mode==='base' && vKey) vBase.addTo(map);
        else if(mode==='sat' && vKey) vSat.addTo(map);
        else osm.addTo(map);
      }catch(e){ osm.addTo(map); }
    }

    function onMsg(raw){
      try{
        const d=typeof raw==='string'?JSON.parse(raw):raw;
        if(d.type==='moveTo'){ const {lat,lng,zoom=16}=d.payload||{}; if(Number.isFinite(lat)&&Number.isFinite(lng)) map.setView([lat,lng],zoom); }
        if(d.type==='showPlaces') addPlaces(d.payload);
        if(d.type==='clearPlaces'){ try{cluster.clearLayers?.();}catch{} tooltipEls.length=0; }
        if(d.type==='switchBase') switchBase(d.payload);
        if(d.type==='resetSeoul') map.setView(center,12);
        if(d.type==='cardsToggle'){ setCardsEnabled(!!d.payload); }
        if(d.type==='clearBounds') clearBounds();
        if(d.type==='showSido') showSido(d.payload);
        if(d.type==='showSgg')  showSgg(d.payload);
        if(d.type==='showEmd')  showEmd(d.payload);
        if(d.type==='showStats') showStats(d.payload);
        if(d.type==='clearStats') clearStats();
      }catch(e){ __post('wvError',{msg:'onMsgFail', detail:String(e)}); }
    }
    window.addEventListener('message',e=>onMsg(e.data));
    document.addEventListener('message',e=>onMsg(e.data));

    setCardsEnabled(true);
    setTimeout(()=>{ __post('ready'); postBounds(); },0);
  </script>
</body>
</html>
`;

/* ───────── RN ↔ WV BRIDGE ───────── */
function useWebBridge(webRef:any, frameRef:any){
  const [ready,setReady]=useState(false);
  const [view,setView]=useState<{north:number;south:number;east:number;west:number;zoom:number}|null>(null);

  const post = useCallback((msg:unknown)=>{
    const payload=JSON.stringify(msg);
    if(isWeb) frameRef.current?.contentWindow?.postMessage(payload,'*');
    else webRef.current?.postMessage(payload);
  },[]);

  const handleMsg = useCallback((msg:any)=>{
    try{
      if(msg.type==='ready') return setReady(true);
      if(msg.type==='bounds') return setView(msg.payload);
      if(msg.type==='wvError'){
        console.warn('[WV]', msg.payload?.msg, msg.payload);
        return;
      }
      if(msg.type==='markerClick') (isWeb?alert:Alert.alert)('단지 선택', msg.payload?.title ?? msg.payload?.name ?? '(이름 없음)');
    }catch(e){}
  },[]);

  const onMessageNative = useCallback((e:any)=>{ try{handleMsg(JSON.parse(e.nativeEvent.data));}catch{} },[handleMsg]);

  useEffect(()=>{ if(!isWeb) return;
    const h=(e:MessageEvent)=>{ try{handleMsg(JSON.parse(String(e.data)));}catch{} };
    window.addEventListener('message',h); return ()=>window.removeEventListener('message',h);
  },[handleMsg]);

  return { ready, view, post, onMessageNative, setReady };
}

/* ───────── MAIN ───────── */

type DailySummary = { sale:number; rent:number; trades:number } | null;

export default function App(){
  const webRef = useRef<WebView>(null);
  const frameRef = useRef<any>(null);
  const { ready, view, post, onMessageNative, setReady } = useWebBridge(webRef, frameRef);

  const [useVworld, setUseVworld] = useState(true);
  const [cardsOn, setCardsOn]     = useState(true);
  const [boundsOn, setBoundsOn]   = useState(true);
  const [search, setSearch]       = useState('');

  // 기간(기본 12m)
  const [period, setPeriod]       = useState<Period>('12m');

  // UX: 요약 + 랭킹 표시 여부
  const [summary, setSummary] = useState<DailySummary>(null);
  const [showRanking, setShowRanking] = useState(false);

  const html = useMemo(()=>buildHtml(useVworld, VWORLD_KEY),[useVworld]);

  /* 마커 로드 (z >= 16에서만) */
  const markersAbortRef = useRef<AbortController|null>(null);
  const fetchMarkers = useMemo(()=>debounce(async(v:NonNullable<typeof view>)=>{
    if(v.zoom < Z.MARKER_MIN) { post({type:'clearPlaces'}); return; }
    markersAbortRef.current?.abort();
    const controller=new AbortController(); markersAbortRef.current=controller;
    try{
      const res = await axiosInstance.get('/api/markers', {
        params:{north:v.north,south:v.south,east:v.east,west:v.west,limit:2000,offset:0,period},
        signal:controller.signal,
      });
      const data = Array.isArray(res.data)?res.data:(res.data??[]);
      post({ type:'showPlaces', payload: data.map((p:any)=>({
        id:p.id, lat:p.lat, lng:p.lng, title:p.name ?? p.title,
        sale_price:p.sale_price ?? 0,
        rent_price:p.rent_price ?? 0,
        sale_tx:   p.sale_tx    ?? 0,     // ⬅ 매매 거래량 전달
        rent_tx:   p.rent_tx    ?? 0,     // ⬅ 전세 거래량 전달
      }))});
    }catch(e){
      if((e as AxiosError).code!=='ERR_CANCELED'){
        console.error('markers error',e);
        (isWeb?alert:Alert.alert)('서버 연결 실패','백엔드 API를 불러올 수 없습니다.');
      }
    }
  },300),[post, period]);

  /* 경계 로드: z16+이면 경계 OFF */
  const boundsAbortRef = useRef<AbortController|null>(null);
  const fetchBounds = useMemo(()=>debounce(async(v:NonNullable<typeof view>)=>{
    if(!boundsOn){ post({type:'clearBounds'}); return; }
    if(v.zoom >= Z.MARKER_MIN){ post({type:'clearBounds'}); return; } // 마커 구간에서는 경계 OFF

    boundsAbortRef.current?.abort();
    const controller=new AbortController(); boundsAbortRef.current=controller;

    const t0 = performance.now();
    const key = `bounds ${v.zoom} ${v.west.toFixed(3)},${v.south.toFixed(3)}~${v.east.toFixed(3)},${v.north.toFixed(3)}`;
    console.time(key);

    const call = async (level:'sido'|'sgg'|'emd')=>{
      const { data } = await axiosInstance.get('/api/bounds',{
        params:{
          west:v.west, south:v.south, east:v.east, north:v.north,
          level, zoom: Math.floor(v.zoom)   // <- 정수로 강제
        },
        signal:controller.signal,
      });
      return data;
    };
    try{
      if(v.zoom >= Z.EMD_MIN && v.zoom <= Z.EMD_MAX){
        const g=await call('emd');  g.features.length ? post({type:'showEmd', payload:g}) : post({type:'clearBounds'});
      }else if(v.zoom >= Z.SGG_MIN && v.zoom <= Z.SGG_MAX){
        const g=await call('sgg'); g.features.length ? post({type:'showSgg', payload:g}) : post({type:'clearBounds'});
      }else if(v.zoom === Z.CITY){
        const g=await call('sido'); g.features.length ? post({type:'showSido',payload:g}) : post({type:'clearBounds'});
      }else{
        post({type:'clearBounds'});
      }
    }catch(e){
      console.warn('[bounds error]', e?.message ?? e);
      post({type:'clearBounds'});
    }finally{
      console.timeEnd(key); // 프론트 총 소요(ms)
      console.log('[bounds features]', { zoom:v.zoom });
    }
  },600),[post,boundsOn]);

  /* 구/동 라벨 불러오기 (mv_*_stats_long) */
const lastGeoKeyRef = useRef<string | null>(null);

const fetchGeoStats = useMemo(
  () =>
    debounce(async (v: NonNullable<typeof view>) => {
      const scope = bandForZoom(v.zoom);
      if (!(scope === "sgg" || scope === "emd")) {
        post({ type: "clearStats" });
        return;
      }

      const key = `${scope}:${period}:${v.zoom}:${v.north.toFixed(3)}:${v.west.toFixed(3)}`;
      if (lastGeoKeyRef.current === key) return;
      lastGeoKeyRef.current = key;

      try {
        const { data } = await axiosInstance.get("/api/geo-summary", {
          params: { scope, period },
        });

        // 뷰포트 안만 라벨 표시
        const { north, south, east, west } = v;
        const inView = (p: any) =>
          p.lat <= north && p.lat >= south && p.lng <= east && p.lng >= west;

        post({
          type: "showStats",
          payload: (Array.isArray(data) ? data : []).filter(inView),
        });
      } catch (e) {
        post({ type: "clearStats" });
      }
    }, 300),
  [period, post]
);


  /* 요약/랭킹: z11 / z12~13 / z14~15 (환경변수 ON일 때만) */
  const lastSummaryKeyRef = useRef<string | null>(null);
  const fetchSummary = useMemo(()=>debounce(async (v:NonNullable<typeof view>)=>{
    if (!STATS_ENABLED) { setSummary(null); return; }
    const scope = bandForZoom(v.zoom);
    if (!scope) { setSummary(null); return; }
    const key = `${scope}:${period}:${v.zoom}:${v.north.toFixed(3)}:${v.west.toFixed(3)}`;
    if (lastSummaryKeyRef.current === key) return;
    lastSummaryKeyRef.current = key;

    try{
      const { data } = await axiosInstance.get('/api/summary', {
        params: { scope, north:v.north, south:v.south, east:v.east, west:v.west }
      });
      setSummary({
        sale:  data?.sale ?? 0,
        rent:  data?.rent ?? 0,
        trades:data?.trades ?? 0,
      });
    } catch {
      setSummary(null);
    }
  }, 300), [period]);

  // 뷰/기간 변화에 따라 데이터 로드
  useEffect(()=>{ if(!ready||!view) return;
    fetchBounds(view);
    fetchMarkers(view);
    fetchGeoStats(view);
    const inRankingZone =
      view.zoom === Z.CITY ||
      (view.zoom >= Z.SGG_MIN && view.zoom <= Z.SGG_MAX) ||
      (view.zoom >= Z.EMD_MIN && view.zoom <= Z.EMD_MAX);
    setShowRanking(STATS_ENABLED && inRankingZone);
    if (STATS_ENABLED && inRankingZone) fetchSummary(view);
    else setSummary(null);
  },[ready,view,fetchBounds,fetchMarkers,fetchGeoStats,fetchSummary]);

  /* 지도 제어 & UI */
  const switchToVBase    = ()=>{ setUseVworld(true); post({type:'switchBase',payload:'base'}); };
  const switchToVSat     = ()=>{ setUseVworld(true); post({type:'switchBase',payload:'sat'}); };
  const resetSeoul       = ()=> post({type:'resetSeoul'});
  const toggleCards      = ()=>{ const next=!cardsOn; setCardsOn(next); post({type:'cardsToggle',payload:next}); };
  const toggleBounds     = ()=>{ const next=!boundsOn; setBoundsOn(next); if(!next) post({type:'clearBounds'}); else if(view) fetchBounds(view); };

  const searchGo = useCallback(async()=>{
    const q=search.trim(); if(!q) return;
    try{
      let { data } = await axiosInstance.get('/api/vworld/search',{ params:{ query:q, type:'address', size:1 }});
      let it = data?.response?.result?.items?.[0];
      let x=parseFloat(it?.point?.x), y=parseFloat(it?.point?.y);
      if(!isFinite(x)||!isFinite(y)){
        const r2=await axiosInstance.get('/api/vworld/search',{ params:{ query:q, type:'place', size:1 }});
        it=r2?.data?.response?.result?.items?.[0]; x=parseFloat(it?.point?.x); y=parseFloat(it?.point?.y);
      }
      if(isFinite(x)&&isFinite(y)) post({type:'moveTo',payload:{lat:y,lng:x,zoom:16}});
      else (isWeb?alert:Alert.alert)('검색 결과 없음','다른 키워드로 시도해보세요.');
    }catch{ (isWeb?alert:Alert.alert)('오류','검색 중 문제가 발생했습니다.'); }
  },[search,post]);

  const goMyLocation = useCallback(async()=>{
    try{
      const { status } = await Location.requestForegroundPermissionsAsync();
      if(status!=='granted') return (isWeb?alert:Alert.alert)('위치 권한이 필요합니다.');
      const { coords } = await Location.getCurrentPositionAsync({});
      post({type:'moveTo',payload:{lat:coords.latitude,lng:coords.longitude,zoom:16}});
    }catch{ (isWeb?alert:Alert.alert)('오류','현재 위치를 가져오지 못했습니다.'); }
  },[post]);

  return (
    <SafeAreaView style={{flex:1,backgroundColor:'#000'}}>
      <StatusBar barStyle="light-content" />
      {isWeb
        ? React.createElement('iframe',{
            ref:frameRef, srcDoc:html, title:'map',
            sandbox:'allow-scripts allow-same-origin',
            style:{flex:1,width:'100%',height:'100%',border:'none'},
            onLoad:()=>setReady(true),
          })
        : <WebView
            ref={webRef}
            originWhitelist={['*']}
            source={{ html }}
            javaScriptEnabled domStorageEnabled
            androidLayerType="hardware" overScrollMode="never"
            setSupportMultipleWindows={false}
            onMessage={onMessageNative} onLoadEnd={()=>setReady(true)}
            onConsoleMessage={(e)=>console.log('[WV]',e.nativeEvent.message)}
            style={{flex:1}}
          />}

      {/* 상단 툴바 */}
      <View style={styles.toolbar}>
        <ToolbarButton label="일반지도" onPress={switchToVBase}/>
        <ToolbarButton label="위성지도" onPress={switchToVSat}/>
        <ToolbarButton label="현재위치" onPress={goMyLocation}/>
        <ToolbarButton label="광화문으로" onPress={resetSeoul}/>
        <ToolbarButton label={`정보카드 ${cardsOn?'ON':'OFF'}`} onPress={toggleCards} active={cardsOn}/>
        <ToolbarButton label={`경계선 ${boundsOn?'ON':'OFF'}`} onPress={toggleBounds} active={boundsOn}/>
        <View style={styles.searchWrap}>
          <TextInput
            value={search} onChangeText={setSearch}
            placeholder="주소/단지명 검색" placeholderTextColor="#cbd5e1"
            style={styles.input} onSubmitEditing={searchGo} returnKeyType="search"
          />
          <TouchableOpacity style={styles.searchBtn} onPress={searchGo}>
            <Text style={styles.searchBtnText}>검색</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* 기간 선택 바 */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={periodStyles.bar}
        contentContainerStyle={periodStyles.barContent}
      >
        {PERIODS.map(p=>{
          const active = p===period;
          return (
            <TouchableOpacity key={p} onPress={()=>setPeriod(p)} style={[periodStyles.pill, active && periodStyles.pillActive]}>
              <Text style={[periodStyles.pillText, active && periodStyles.pillTextActive]}>
                {PERIOD_LABEL[p]}
              </Text>
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      {/* 요약 바 + 랭킹 카드 (z11/12~13/14~15 구간에서만, STATS_ENABLED=1 일 때만 보임) */}
      <SummaryBar data={STATS_ENABLED ? summary : null} />
      <RankingCard visible={STATS_ENABLED && showRanking} />
    </SafeAreaView>
  );
}

/* ───────── UI ───────── */
function ToolbarButton({label,onPress,active=false}:{label:string;onPress:()=>void;active?:boolean}){
  return (
    <TouchableOpacity style={[styles.btn, active&&styles.btnActive]} onPress={onPress} activeOpacity={0.85}>
      <Text style={styles.btnText}>{label}</Text>
    </TouchableOpacity>
  );
}

function SummaryBar({ data }: { data: DailySummary }) {
  if (!data) return null;
  return (
    <View style={uxStyles.summaryBar}>
      <Text style={uxStyles.sumText}>
        매매가: {fmtWon(data.sale)}  ·  전세가: {fmtWon(data.rent)}  ·  거래량: {data.trades.toLocaleString()}건
      </Text>
    </View>
  );
}

function RankingCard({ visible }: { visible:boolean }) {
  if (!visible) return null;
  return (
    <View style={uxStyles.ranking}>
      <Text style={uxStyles.rankTitle}>랭킹 (DEMO)</Text>
      <Text style={uxStyles.rankSub}>차트/지표는 추후 연결</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  toolbar:{
    position:'absolute',top:0,left:0,right:0,height:TOOLBAR_H,
    paddingHorizontal:8,gap:8,backgroundColor:'#0b1220',
    flexDirection:'row',alignItems:'center',zIndex:10,elevation:10,
  },
  btn:{ paddingHorizontal:12,paddingVertical:8,backgroundColor:'#243b80',borderRadius:8,borderWidth:1,borderColor:'#334155' },
  btnActive:{ backgroundColor:'#2f6fed' },
  btnText:{ color:'#fff',fontWeight:'700' },
  searchWrap:{ flexDirection:'row',alignItems:'center',marginLeft:6,gap:6,flex:1 },
  input:{ flex:1,height:36,borderRadius:8,paddingHorizontal:10,backgroundColor:'#111827',color:'#fff',borderWidth:1,borderColor:'#334155' },
  searchBtn:{ paddingHorizontal:12,height:36,borderRadius:8,alignItems:'center',justifyContent:'center',backgroundColor:'#2f6fed' },
  searchBtnText:{ color:'#fff',fontWeight:'700' },
});

const uxStyles = StyleSheet.create({
  summaryBar:{
    position:'absolute', top: TOOLBAR_H + 38, left:0, right:0,
    paddingVertical:6, paddingHorizontal:10,
    backgroundColor:'rgba(12,18,34,.88)', borderBottomWidth:1, borderColor:'#1f2a44',
    zIndex: 9,
  },
  sumText:{ color:'#e6eefc', textAlign:'center', fontWeight:'700' },
  ranking:{
    position:'absolute', top: TOOLBAR_H+80, right: 10, width: 220,
    backgroundColor:'rgba(12,18,34,.92)', borderRadius:12, padding:12, gap:6,
    borderWidth:1, borderColor:'#1f2a44', zIndex:9,
  },
  rankTitle:{ color:'#fff', fontWeight:'800' },
  rankSub:{ color:'#cbd5e1' },
});

/* 기간 선택 바 스타일 */
const periodStyles = StyleSheet.create({
  bar:{
    position:'absolute',
    top: TOOLBAR_H, left:0, right:0,
    height: 38,
    backgroundColor:'rgba(8,12,24,.9)',
    zIndex: 9,
    borderBottomWidth:1, borderColor:'#1f2a44',
  },
  barContent:{
    paddingHorizontal:8, alignItems:'center', gap:8,
  },
  pill:{
    paddingHorizontal:10, paddingVertical:6, borderRadius:9999,
    borderWidth:1, borderColor:'#334155',
    backgroundColor:'#0b1220',
  },
  pillActive:{
    backgroundColor:'#2f6fed', borderColor:'#2f6fed',
  },
  pillText:{ color:'#cbd5e1', fontWeight:'700', fontSize:12 },
  pillTextActive:{ color:'#fff' },
});

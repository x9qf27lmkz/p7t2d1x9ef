// frontend/App.tsx
import React, {
  useMemo,
  useRef,
  useCallback,
  useState,
  useEffect,
} from 'react';
import {
  SafeAreaView,
  StatusBar,
  View,
  Alert,
  TouchableOpacity,
  Text,
  StyleSheet,
  Platform,
  TextInput,
  ScrollView,
  ActivityIndicator,
} from 'react-native';
import { WebView } from 'react-native-webview';
import * as Location from 'expo-location';
import axios, { AxiosError } from 'axios';

/* ───────── CONFIG ───────── */
const VWORLD_KEY = process.env.EXPO_PUBLIC_VWORLD_KEY ?? '';
const TOOLBAR_H = 56;

/** 카드(툴팁) 노출 임계 줌: z17부터 카드 표시 */
const LABEL_ZOOM = 17;

const isWeb = Platform.OS === 'web';

/** 요약/랭킹 기능 ON/OFF (기본 OFF: 404 스팸 방지) */
const STATS_ENABLED = process.env.EXPO_PUBLIC_STATS_ENABLED === '1';

/** 줌 UX 구간 정의 */
const Z = {
  CITY: 11, // 서울 시 경계
  SGG_MIN: 12, // 구 경계 12~13
  SGG_MAX: 13,
  EMD_MIN: 14, // 동 경계 14~16
  EMD_MAX: 16,
  MARKER_MIN: 17, // 마커/카드 17+
} as const;

/* ───────── PERIOD ───────── */
const PERIODS = ['1w', '1m', '3m', '6m', '12m', '24m', '36m'] as const;
type Period = (typeof PERIODS)[number];

const PERIOD_LABEL: Record<Period, string> = {
  '1w': '1주',
  '1m': '1개월',
  '3m': '3개월',
  '6m': '6개월',
  '12m': '12개월',
  '24m': '24개월',
  '36m': '36개월',
};

/* ───────── UTILS ───────── */
function detectApiBase() {
  if (typeof window !== 'undefined') {
    // 같은 머신에서 백엔드 8000 띄운 상태 기준
    return `http://${window.location.hostname}:8000`;
  }
  const envBase = process.env.EXPO_PUBLIC_API_BASE;
  return (envBase?.trim() || 'http://192.168.0.12:8000').replace(/\/+$/, '');
}

function debounce<F extends (...a: any[]) => void>(fn: F, ms = 250) {
  let t: any;
  return (...a: Parameters<F>) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...a), ms);
  };
}

const fmtWon = (v: number) => (v === 0 ? '—' : `${v.toLocaleString()}억`);

const bandForZoom = (zoom: number) =>
  zoom === Z.CITY
    ? 'city'
    : zoom >= Z.SGG_MIN && zoom <= Z.SGG_MAX
    ? 'sgg'
    : zoom >= Z.EMD_MIN && zoom <= Z.EMD_MAX
    ? 'emd'
    : null;

/* ───────── AXIOS ───────── */
const API_BASE = detectApiBase();
const BASIC_AUTH = process.env.EXPO_PUBLIC_API_BASIC_AUTH || '';

const axiosInstance = axios.create({
  baseURL: API_BASE,
  headers: BASIC_AUTH
    ? {
        Authorization:
          'Basic ' +
          (typeof btoa !== 'undefined'
            ? btoa(BASIC_AUTH)
            : // @ts-ignore
              Buffer.from(BASIC_AUTH).toString('base64')),
      }
    : undefined,
  timeout: 30000,
});

/* ───────── WV HTML (지도/경계/카드 토글 등) ───────── */
const buildHtml = (useVworld: boolean, vworldKey: string) => `
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

    .leaflet-control-container .leaflet-top{margin-top:${TOOLBAR_H}px}

    .leaflet-top.leaflet-left{
      top:90px!important;
      left:10px!important;
      z-index:500;
    }

    .zoom-badge{
      background:#111;color:#fff;border-radius:10px;padding:4px 8px;
      font-size:12px;font-weight:700;box-shadow:0 2px 8px rgba(0,0,0,.25)
    }
    #zoomLevelBadge{
      position:absolute;
      left:15px;
      top:230px;
      background:#111;
      color:#fff;
      border-radius:10px;
      padding:4px 8px;
      font-size:12px;
      font-weight:700;
      box-shadow:0 2px 8px rgba(0,0,0,.25);
      z-index:1000;
    }

    .leaflet-tooltip.apt-card-tt{
      background:transparent;border:none;box-shadow:none;z-index:9999;pointer-events:none
    }
    .cards-off .leaflet-tooltip.apt-card-tt{display:none!important;}

    .apt-card{
      background:#FAF9F6;border:1px solid #E2E2E2;border-radius:12px;
      box-shadow:0 4px 14px rgba(0,0,0,.15);padding:8px 10px;min-width:160px;
      color:#1C1C1C;font-family:'Noto Serif KR','Noto Serif','Pretendard',system-ui,-apple-system,sans-serif;
      line-height:1.35;text-align:center;
      transform:scale(.7);transform-origin:top center;
    }
    .apt-card .line{font-size:14px;font-weight:700}
    .apt-card .name{font-size:16px;font-weight:800;color:#0f172a;margin:2px 0}
    .apt-card .tx{font-size:14px;color:#6b7280;text-align:center}

    .marker-cluster div{
      background:#2f6fed;color:#fff;font-weight:800;border-radius:50%;
      width:32px;height:32px;display:flex;align-items:center;justify-content:center;
      box-shadow:0 2px 10px rgba(47,111,237,.35);font-size:12px;border:2px solid #fff
    }

    .stat-label{
      background:#ffffff;
      color:#0f172a;
      border:1px solid #E2E8F0;
      border-radius:12px;
      padding:6px 10px;
      min-width:140px;
      text-align:center;
      font-size:12px;
      font-weight:700;
      line-height:1.35;
      box-shadow:0 4px 14px rgba(0,0,0,.15);
      white-space:nowrap;
      pointer-events:none;
      transform: translate(-50%, -100%);
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
    const __post=(type,payload)=>{
      try{window.parent?.postMessage(JSON.stringify({type,payload}),'*');}catch(e){}
      try{window.ReactNativeWebView?.postMessage(JSON.stringify({type,payload}));}catch(e){}
    };
    window.onerror=(msg,src,line,col,err)=>{
      __post('wvError',{msg:String(msg),src,line,col,stack:String(err?.stack||'')});
    };
    window.addEventListener('unhandledrejection',e=>{
      __post('wvError',{msg:String(e.reason),stack:String(e.reason?.stack||'')});
    });
  </script>

  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin></script>
  <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>

  <script>
    const center=[37.5714,126.9768];
    const map=L.map('map',{zoomControl:true,preferCanvas:true}).setView(center,12);

    const osm=L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap'});
    const vKey=${JSON.stringify(vworldKey || '')};
    const vBase=L.tileLayer('https://api.vworld.kr/req/wmts/1.0.0/'+vKey+'/Base/{z}/{y}/{x}.png?tileMatrixSet=EPSG:3857',{attribution:'© VWorld'});
    const vSat =L.tileLayer('https://api.vworld.kr/req/wmts/1.0.0/'+vKey+'/Satellite/{z}/{y}/{x}.jpeg?tileMatrixSet=EPSG:3857',{attribution:'© VWorld'});

    try{
      if(${useVworld}&&vKey){
        vBase.addTo(map);
      }else{
        osm.addTo(map);
      }
    }catch(e){
      __post('wvError',{msg:'baseLayerFail',detail:String(e)});
      osm.addTo(map);
    }

    const zoomBadge=document.getElementById('zoomLevelBadge');
    const updateZ=()=>{
      if(zoomBadge) zoomBadge.textContent='Z:'+map.getZoom();
    };
    map.on('zoomend moveend',updateZ);updateZ();

    const RN=window.ReactNativeWebView;
    const LABEL_ZOOM=${LABEL_ZOOM};
    let cardsEnabled=true;

    // cluster
    const mkCluster=()=>{
      try{
        if(L.markerClusterGroup){
          return L.markerClusterGroup({
            chunkedLoading:true,
            maxClusterRadius:60,
            spiderfyOnMaxZoom:true,
            disableClusteringAtZoom:LABEL_ZOOM,
            iconCreateFunction:c=>L.divIcon({
              html:'<div>'+c.getChildCount()+'</div>',
              className:'marker-cluster',
              iconSize:L.point(36,36)
            })
          }).addTo(map);
        }
      }catch(e){}
      __post('wvError',{msg:'clusterPluginMissing'});
      return L.featureGroup().addTo(map);
    };
    const cluster=mkCluster();

    /* ====== 구/동 통계 라벨 ====== */
    const labelsPane=map.createPane('labels');
    labelsPane.style.zIndex=460;
    labelsPane.style.pointerEvents='none';
    const statsLayer=L.featureGroup({pane:'labels'}).addTo(map);

    function clearStats(){
      try{statsLayer.clearLayers();}catch(e){}
    }

    function showStats(list){
      clearStats();
      (list||[]).forEach(it=>{
        if(!Number.isFinite(it.lat)||!Number.isFinite(it.lng))return;

        const money=(v)=>{
          const n=Number(v??0);
          if(!Number.isFinite(n))return "—";
          return n.toLocaleString(undefined,{
            minimumFractionDigits:1,
            maximumFractionDigits:1
          });
        };
        const saleTx=Number(it.sale_tx??0);
        const rentTx=Number(it.rent_tx??0);

        const html=
          "<div class='stat-label'>"
          +"<div class='line'>매매가 "+money(it.sale_med)+"억</div>"
          +"<div class='line'>매매량 "+saleTx.toLocaleString()+"건</div>"
          +"<div class='name'>"+(it.name||'')+"</div>"
          +"<div class='line'>전세가 "+money(it.rent_med)+"억</div>"
          +"<div class='line'>전세량 "+rentTx.toLocaleString()+"건</div>"
          +"</div>";

        const icon=L.divIcon({className:'',html,iconAnchor:[0,0]});
        L.marker([it.lat,it.lng],{icon,interactive:false}).addTo(statsLayer);
      });
    }

    // marker tooltip/card layer
    const tooltipEls=[];
    const icon=L.icon({
      iconUrl:"data:image/svg+xml;utf8,"+
        "<svg xmlns='http://www.w3.org/2000/svg' width='56' height='56' viewBox='0 0 64 64'>"+
        "<rect x='10' y='46' width='44' height='8' rx='2' fill='rgb(96,165,250)'/>"+
        "<rect x='10' y='24' width='12' height='22' rx='2' fill='rgb(59,130,246)'/>"+
        "<rect x='26' y='18' width='12' height='28' rx='2' fill='rgb(59,130,246)'/>"+
        "<rect x='42' y='24' width='12' height='22' rx='2' fill='rgb(59,130,246)'/>"+
        "</svg>",
      iconSize:[56,56],
      iconAnchor:[28,56]
    });

    function updateCardsVisibility(){
      const show=(map.getZoom()>=LABEL_ZOOM)&&cardsEnabled;
      tooltipEls.forEach(el=>{
        if(el)el.style.display=show?'':'none';
      });
    }

    function setCardsEnabled(v){
      cardsEnabled=!!v;
      document.documentElement.classList.toggle('cards-off',!cardsEnabled);
      updateCardsVisibility();
    }

    function money(v){
      const n=Number(v??0);
      if(!Number.isFinite(n))return '0.0억';
      return n.toLocaleString(undefined,{
        minimumFractionDigits:1,
        maximumFractionDigits:1
      })+'억';
    }

    function addPlaces(list){

      console.log('[WV] addPlaces called', list?.length);
      try{cluster.clearLayers?.();}catch(e){}
      tooltipEls.length=0;

      (list||[]).forEach(p=>{
        if(!Number.isFinite(p.lat)||!Number.isFinite(p.lng))return;

        const m=L.marker([p.lat,p.lng],{icon});

        const html=
          "<div class='apt-card'>"
          +"<div class='line'>매매가 "+money(p.sale_price)+"</div>"
          +"<div class='line'>매매량 "+Number(p.sale_tx||0).toLocaleString()+"건</div>"
          +"<div class='name'>"+(p.apt_nm||p.title||'—')+"</div>"
          +"<div class='line'>전세가 "+money(p.rent_price)+"</div>"
          +"<div class='line'>전세량 "+Number(p.rent_tx||0).toLocaleString()+"건</div>"
          +"</div>";

        const tt=m.bindTooltip(html,{
          permanent:true,
          direction:'bottom',
          className:'leaflet-tooltip apt-card-tt'
        }).getTooltip();

        const el=tt?.getElement();
        if(el)tooltipEls.push(el);

        m.on('click',()=>{
          const payload = {
            apt_cd: p.apt_cd ?? p.id ?? '',
            apt_nm: p.apt_nm ?? p.title ?? '',
          };

          // iframe -> 부모(웹) / RN 쪽으로 공통 브로드캐스트
          try {
            window.parent?.postMessage(
              JSON.stringify({ type:'markerClick', payload }),
              '*'
            );
          } catch(e){}

          try {
            window.ReactNativeWebView?.postMessage(
              JSON.stringify({ type:'markerClick', payload })
            );
          } catch(e){}
        });

        cluster.addLayer(m);
      });
      updateCardsVisibility();
    }

    map.on('zoomend',updateCardsVisibility);

    /* ====== 경계 레이어 (행정구역 폴리곤) ====== */
    const boundsPane=map.createPane('bounds');
    boundsPane.style.zIndex=450;
    boundsPane.style.pointerEvents='none';

    let sidoLayer=null,sggLayer=null,emdLayer=null;

    function clearBounds(){
      [sidoLayer,sggLayer,emdLayer].forEach(l=>{
        if(l){try{map.removeLayer(l);}catch(e){}}
      });
      sidoLayer=sggLayer=emdLayer=null;
    }

    function showSido(fc){
      if(sidoLayer)map.removeLayer(sidoLayer);
      sidoLayer=L.geoJSON(fc,{
        pane:'bounds',interactive:false,
        style:()=>({color:'#64748b',weight:2,dashArray:'3,6',fill:false})
      }).addTo(map);
    }
    function showSgg(fc){
      if(sggLayer)map.removeLayer(sggLayer);
      sggLayer=L.geoJSON(fc,{
        pane:'bounds',interactive:false,
        style:()=>({color:'#1f6feb',weight:2.5,dashArray:'4,4',fill:false})
      }).addTo(map);
    }
    function showEmd(fc){
      if(emdLayer)map.removeLayer(emdLayer);
      emdLayer=L.geoJSON(fc,{
        pane:'bounds',interactive:false,
        style:()=>({color:'#16a34a',weight:1.5,fillColor:'#16a34a',fillOpacity:0.08})
      }).addTo(map);
    }

    function postBounds(){
      const b=map.getBounds();
      const payload={
        type:'bounds',
        payload:{
          north:b.getNorth(),
          south:b.getSouth(),
          east:b.getEast(),
          west:b.getWest(),
          zoom:map.getZoom(),
        }
      };
      try{window.ReactNativeWebView?.postMessage(JSON.stringify(payload));}catch(e){}
      try{window.parent?.postMessage(JSON.stringify(payload),'*');}catch(e){}
    }
    map.on('moveend zoomend',postBounds);

    function switchBase(mode){
      [osm,vBase,vSat].forEach(l=>{try{map.removeLayer(l);}catch(e){}});
      try{
        if(mode==='base'&&vKey)vBase.addTo(map);
        else if(mode==='sat'&&vKey)vSat.addTo(map);
        else osm.addTo(map);
      }catch(e){
        osm.addTo(map);
      }
    }

    function onMsg(raw){
      try{
        const d=typeof raw==='string'?JSON.parse(raw):raw;
        if(d.type==='moveTo'){
          const {lat,lng,zoom=16}=d.payload||{};
          if(Number.isFinite(lat)&&Number.isFinite(lng)){
            map.setView([lat,lng],zoom);
          }
        }
        if(d.type==='showPlaces')addPlaces(d.payload);
        if(d.type==='clearPlaces'){
          try{cluster.clearLayers?.();}catch(e){}
          tooltipEls.length=0;
        }
        if(d.type==='switchBase')switchBase(d.payload);
        if(d.type==='resetSeoul')map.setView(center,12);
        if(d.type==='cardsToggle'){setCardsEnabled(!!d.payload);}
        if(d.type==='clearBounds')clearBounds();
        if(d.type==='showSido')showSido(d.payload);
        if(d.type==='showSgg') showSgg(d.payload);
        if(d.type==='showEmd') showEmd(d.payload);
        if(d.type==='showStats')showStats(d.payload);
        if(d.type==='clearStats')clearStats();
      }catch(e){
        __post('wvError',{msg:'onMsgFail',detail:String(e)});
      }
    }

    window.addEventListener('message',e=>onMsg(e.data));
    document.addEventListener('message',e=>onMsg(e.data));

    setCardsEnabled(true);
    setTimeout(()=>{__post('ready');postBounds();},0);
  </script>
</body>
</html>
`;

/* ───────── RN ↔ WV BRIDGE ───────── */
function useWebBridge(webRef: any, frameRef: any) {
  const [ready, setReady] = useState(false);
  const [view, setView] = useState<{
    north: number;
    south: number;
    east: number;
    west: number;
    zoom: number;
  } | null>(null);

  // ✅ 새로 추가: 사용자가 클릭한 마커 정보
  const [clickedMarker, setClickedMarker] = useState<{
    apt_cd?: string;
    apt_nm?: string;
  } | null>(null);

  const post = useCallback(
    (msg: unknown) => {
      const payload = JSON.stringify(msg);
      if (isWeb) {
        frameRef.current?.contentWindow?.postMessage(payload, '*');
      } else {
        webRef.current?.postMessage(payload);
      }
    },
    []
  );

  const handleMsg = useCallback((msg: any) => {
    try {
      if (msg.type === 'ready') {
        setReady(true);
        return;
      }
      if (msg.type === 'bounds') {
        setView(msg.payload);
        return;
      }
      if (msg.type === 'wvError') {
        console.warn('[WV]', msg.payload?.msg, msg.payload);
        return;
      }
      if (msg.type === 'markerClick') {
        // ✅ 여기서 선택된 단지 정보 set
        setClickedMarker(msg.payload || null);
        return;
      }
    } catch (e) {
      console.warn('handleMsg err', e);
    }
  }, []);

  const onMessageNative = useCallback(
    (e: any) => {
      try {
        handleMsg(JSON.parse(e.nativeEvent.data));
      } catch (err) {
        console.warn('onMessageNative parse fail', err);
      }
    },
    [handleMsg]
  );

  useEffect(() => {
    if (!isWeb) return;
    const h = (e: MessageEvent) => {
      try {
        handleMsg(JSON.parse(String(e.data)));
      } catch (err) {
        // ignore
      }
    };
    window.addEventListener('message', h);
    return () => window.removeEventListener('message', h);
  }, [handleMsg]);

  return { ready, view, post, onMessageNative, setReady, clickedMarker };
}

/* ───────── TYPES ───────── */
type DailySummary = { sale: number; rent: number; trades: number } | null;

type AptBasic = {
  apt_cd: string;
  apt_nm: string;
  apt_rdn_addr: string | null;
  whol_dong_cnt: number | null;
  tnohsh: number | null;
  use_aprv_ymd: string | null;
  lat: number | null;
  lng: number | null;
};

/* ───────── MAIN COMPONENT ───────── */
export default function App() {
  const webRef = useRef<WebView>(null);
  const frameRef = useRef<any>(null);

  const {
    ready,
    view,
    post,
    onMessageNative,
    setReady,
    clickedMarker,
  } = useWebBridge(webRef, frameRef);

  const [useVworld, setUseVworld] = useState(true);
  const [cardsOn, setCardsOn] = useState(true);
  const [boundsOn, setBoundsOn] = useState(true);
  const [search, setSearch] = useState('');

  const [period, setPeriod] = useState<Period>('12m');

  const [summary, setSummary] = useState<DailySummary>(null);
  const [showRanking, setShowRanking] = useState(false);

  // ✅ 선택된 단지 상세
  const [selectedApt, setSelectedApt] = useState<AptBasic | null>(null);
  const [loadingApt, setLoadingApt] = useState(false);

  const html = useMemo(
    () => buildHtml(useVworld, VWORLD_KEY),
    [useVworld]
  );

  /* ───── 마커 로드 ───── */
  const markersAbortRef = useRef<AbortController | null>(null);
  const fetchMarkers = useMemo(
    () =>
      debounce(async (v: NonNullable<typeof view>) => {
        if (v.zoom < Z.MARKER_MIN) {
          post({ type: 'clearPlaces' });
          return;
        }

        markersAbortRef.current?.abort();
        const controller = new AbortController();
        markersAbortRef.current = controller;

        try {
          const res = await axiosInstance.get('/api/markers', {
            params: {
              min_lat: v.south,
              max_lat: v.north,
              min_lng: v.west,
              max_lng: v.east,
              limit: 2000,
              offset: 0,
            },
            signal: controller.signal,
          });

          const rows = Array.isArray(res.data) ? res.data : res.data ?? [];

          // markers API가 주는 필드: apt_cd, apt_name, lat, lng
          // WebView 쪽에선 apt_cd / apt_nm / lat / lng / sale_price... 형태를 기대하게 맞춰줌
          const mapped = rows.map((p: any) => ({
            apt_cd: p.apt_cd ?? '',
            apt_nm: p.apt_name ?? '',
            lat: p.lat,
            lng: p.lng,
            // 분석지표는 basic 카드 단계에서 필요 없음 → 0으로 채움
            sale_price: 0,
            rent_price: 0,
            sale_tx: 0,
            rent_tx: 0,
          }));

          post({ type: 'showPlaces', payload: mapped });
        } catch (e) {
          if ((e as AxiosError).code !== 'ERR_CANCELED') {
            console.error('markers error', e);
            (isWeb ? alert : Alert.alert)(
              '서버 연결 실패',
              '마커 정보를 불러오지 못했습니다.'
            );
          }
        }
      }, 300),
    [post]
  );

  /* ───── 경계선 폴리곤 ───── */
  const boundsAbortRef = useRef<AbortController | null>(null);
  const fetchBounds = useMemo(
    () =>
      debounce(async (v: NonNullable<typeof view>) => {
        if (!boundsOn) {
          post({ type: 'clearBounds' });
          return;
        }
        if (v.zoom >= Z.MARKER_MIN) {
          post({ type: 'clearBounds' });
          return;
        }

        boundsAbortRef.current?.abort();
        const controller = new AbortController();
        boundsAbortRef.current = controller;

        const key = `bounds ${v.zoom} ${v.west.toFixed(
          3
        )},${v.south.toFixed(3)}~${v.east.toFixed(
          3
        )},${v.north.toFixed(3)}`;
        console.time(key);

        const call = async (level: 'sido' | 'sgg' | 'emd') => {
          const { data } = await axiosInstance.get('/api/bounds', {
            params: {
              west: v.west,
              south: v.south,
              east: v.east,
              north: v.north,
              level,
              zoom: Math.floor(v.zoom),
            },
            signal: controller.signal,
          });
          return data;
        };

        try {
          if (v.zoom >= Z.EMD_MIN && v.zoom <= Z.EMD_MAX) {
            const g = await call('emd');
            g.features.length
              ? post({ type: 'showEmd', payload: g })
              : post({ type: 'clearBounds' });
          } else if (v.zoom >= Z.SGG_MIN && v.zoom <= Z.SGG_MAX) {
            const g = await call('sgg');
            g.features.length
              ? post({ type: 'showSgg', payload: g })
              : post({ type: 'clearBounds' });
          } else if (v.zoom === Z.CITY) {
            const g = await call('sido');
            g.features.length
              ? post({ type: 'showSido', payload: g })
              : post({ type: 'clearBounds' });
          } else {
            post({ type: 'clearBounds' });
          }
        } catch (e) {
          console.warn('[bounds error]', (e as any)?.message ?? e);
          post({ type: 'clearBounds' });
        } finally {
          console.timeEnd(key);
        }
      }, 600),
    [post, boundsOn]
  );

  /* ───── 구/동 통계 라벨 ───── */
  const lastGeoKeyRef = useRef<string | null>(null);
  const fetchGeoStats = useMemo(
    () =>
      debounce(async (v: NonNullable<typeof view>) => {
        const scope = bandForZoom(v.zoom);
        if (!(scope === 'sgg' || scope === 'emd')) {
          post({ type: 'clearStats' });
          return;
        }

        const key = `${scope}:${period}:${v.zoom}:${v.north.toFixed(
          3
        )}:${v.west.toFixed(3)}`;
        if (lastGeoKeyRef.current === key) return;
        lastGeoKeyRef.current = key;

        try {
          const { data } = await axiosInstance.get('/api/geo-summary', {
            params: { scope, period },
          });

          const { north, south, east, west } = v;
          const inView = (p: any) =>
            p.lat <= north &&
            p.lat >= south &&
            p.lng <= east &&
            p.lng >= west;

          post({
            type: 'showStats',
            payload: (Array.isArray(data) ? data : []).filter(inView),
          });
        } catch {
          post({ type: 'clearStats' });
        }
      }, 300),
    [period, post]
  );

  /* ───── 상단 요약/랭킹 바 ───── */
  const lastSummaryKeyRef = useRef<string | null>(null);
  const fetchSummary = useMemo(
    () =>
      debounce(async (v: NonNullable<typeof view>) => {
        if (!STATS_ENABLED) {
          setSummary(null);
          return;
        }

        const scope = bandForZoom(v.zoom);
        if (!scope) {
          setSummary(null);
          return;
        }

        const key = `${scope}:${period}:${v.zoom}:${v.north.toFixed(
          3
        )}:${v.west.toFixed(3)}`;
        if (lastSummaryKeyRef.current === key) return;
        lastSummaryKeyRef.current = key;

        try {
          const { data } = await axiosInstance.get('/api/summary', {
            params: {
              scope,
              north: v.north,
              south: v.south,
              east: v.east,
              west: v.west,
            },
          });

          setSummary({
            sale: data?.sale ?? 0,
            rent: data?.rent ?? 0,
            trades: data?.trades ?? 0,
          });
        } catch {
          setSummary(null);
        }
      }, 300),
    [period]
  );

  /* ───── view/period 변경 시 데이터 로드 ───── */
  useEffect(() => {
    if (!ready || !view) return;

    // 1) 행정경계
    fetchBounds(view);

    // 2) 단지 마커
    fetchMarkers(view);

    // 3) 구/동 라벨
    fetchGeoStats(view);

    // 4) 상단 요약/랭킹
    const inRankingZone =
      view.zoom === Z.CITY ||
      (view.zoom >= Z.SGG_MIN && view.zoom <= Z.SGG_MAX) ||
      (view.zoom >= Z.EMD_MIN && view.zoom <= Z.EMD_MAX);

    setShowRanking(STATS_ENABLED && inRankingZone);

    if (STATS_ENABLED && inRankingZone) {
      fetchSummary(view);
    } else {
      setSummary(null);
    }
  }, [
    ready,
    view,
    fetchBounds,
    fetchMarkers,
    fetchGeoStats,
    fetchSummary,
  ]);

  /* ───── 마커 클릭 → 단지 기본정보 카드 로드 ───── */
  useEffect(() => {
    if (!clickedMarker) return;

    const apt_cd =
      clickedMarker.apt_cd ||
      // 백업 키 이름들 혹시 대비
      (clickedMarker as any).id ||
      (clickedMarker as any).aptId ||
      null;

    if (!apt_cd) return;

    (async () => {
      try {
        setLoadingApt(true);
        const res = await axiosInstance.get('/api/aptinfo/basic', {
          params: { apt_cd },
        });
        // expecting schema:
        // {
        //   apt_cd, apt_nm, apt_rdn_addr, whol_dong_cnt,
        //   tnohsh, use_aprv_ymd, lat, lng
        // }
        setSelectedApt(res.data || null);
      } catch (e) {
        console.warn('aptinfo/basic error', e);
        (isWeb ? alert : Alert.alert)(
          '불러오기 실패',
          '단지 기본정보를 불러오지 못했습니다.'
        );
      } finally {
        setLoadingApt(false);
      }
    })();
  }, [clickedMarker]);

  /* ───── 지도 제어 & 상단 UI ───── */
  const switchToVBase = () => {
    setUseVworld(true);
    post({ type: 'switchBase', payload: 'base' });
  };

  const switchToVSat = () => {
    setUseVworld(true);
    post({ type: 'switchBase', payload: 'sat' });
  };

  const resetSeoul = () => post({ type: 'resetSeoul' });

  const toggleCards = () => {
    const next = !cardsOn;
    setCardsOn(next);
    post({ type: 'cardsToggle', payload: next });
  };

  const toggleBounds = () => {
    const next = !boundsOn;
    setBoundsOn(next);
    if (!next) {
      post({ type: 'clearBounds' });
    } else if (view) {
      fetchBounds(view);
    }
  };

  const searchGo = useCallback(async () => {
    const q = search.trim();
    if (!q) return;

    try {
      // 1차 주소검색
      let { data } = await axiosInstance.get('/api/vworld/search', {
        params: { query: q, type: 'address', size: 1 },
      });

      let it = data?.response?.result?.items?.[0];
      let x = parseFloat(it?.point?.x);
      let y = parseFloat(it?.point?.y);

      if (!isFinite(x) || !isFinite(y)) {
        // 2차 장소검색
        const r2 = await axiosInstance.get('/api/vworld/search', {
          params: { query: q, type: 'place', size: 1 },
        });
        it = r2?.data?.response?.result?.items?.[0];
        x = parseFloat(it?.point?.x);
        y = parseFloat(it?.point?.y);
      }

      if (isFinite(x) && isFinite(y)) {
        post({ type: 'moveTo', payload: { lat: y, lng: x, zoom: 16 } });
      } else {
        (isWeb ? alert : Alert.alert)(
          '검색 결과 없음',
          '다른 키워드로 시도해보세요.'
        );
      }
    } catch {
      (isWeb ? alert : Alert.alert)(
        '오류',
        '검색 중 문제가 발생했습니다.'
      );
    }
  }, [search, post]);

  const goMyLocation = useCallback(async () => {
    try {
      const { status } =
        await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted')
        return (isWeb ? alert : Alert.alert)(
          '위치 권한이 필요합니다.'
        );

      const { coords } = await Location.getCurrentPositionAsync({});
      post({
        type: 'moveTo',
        payload: {
          lat: coords.latitude,
          lng: coords.longitude,
          zoom: 16,
        },
      });
    } catch {
      (isWeb ? alert : Alert.alert)(
        '오류',
        '현재 위치를 가져오지 못했습니다.'
      );
    }
  }, [post]);

  /* ───── RENDER ───── */
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: '#000' }}>
      <StatusBar barStyle="light-content" />

      {isWeb ? (
        React.createElement('iframe', {
          ref: frameRef,
          srcDoc: html,
          title: 'map',
          sandbox: 'allow-scripts allow-same-origin allow-popups allow-modals allow-forms allow-pointer-lock allow-presentation',
          style: { flex: 1, width: '100%', height: '100%', border: 'none' },
          onLoad: () => setReady(true),
        })
      ) : (
        <WebView
          ref={webRef}
          originWhitelist={['*']}
          source={{ html }}
          javaScriptEnabled
          domStorageEnabled
          androidLayerType="hardware"
          overScrollMode="never"
          setSupportMultipleWindows={false}
          onMessage={onMessageNative}
          onLoadEnd={() => setReady(true)}
          onConsoleMessage={(e) =>
            console.log('[WV]', e.nativeEvent.message)
          }
          style={{ flex: 1 }}
        />
      )}

      {/* 상단 툴바 */}
      <View style={styles.toolbar}>
        <ToolbarButton label="일반지도" onPress={switchToVBase} />
        <ToolbarButton label="위성지도" onPress={switchToVSat} />
        <ToolbarButton label="현재위치" onPress={goMyLocation} />
        <ToolbarButton label="광화문으로" onPress={resetSeoul} />

        <ToolbarButton
          label={`정보카드 ${cardsOn ? 'ON' : 'OFF'}`}
          onPress={toggleCards}
          active={cardsOn}
        />

        <ToolbarButton
          label={`경계선 ${boundsOn ? 'ON' : 'OFF'}`}
          onPress={toggleBounds}
          active={boundsOn}
        />

        <View style={styles.searchWrap}>
          <TextInput
            value={search}
            onChangeText={setSearch}
            placeholder="주소/단지명 검색"
            placeholderTextColor="#cbd5e1"
            style={styles.input}
            onSubmitEditing={searchGo}
            returnKeyType="search"
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
        {PERIODS.map((p) => {
          const active = p === period;
          return (
            <TouchableOpacity
              key={p}
              onPress={() => setPeriod(p)}
              style={[
                periodStyles.pill,
                active && periodStyles.pillActive,
              ]}
            >
              <Text
                style={[
                  periodStyles.pillText,
                  active && periodStyles.pillTextActive,
                ]}
              >
                {PERIOD_LABEL[p]}
              </Text>
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      {/* 요약 바 */}
      <SummaryBar data={STATS_ENABLED ? summary : null} />

      {/* 랭킹 카드 */}
      <RankingCard visible={STATS_ENABLED && showRanking} />

      {/* 선택된 단지 카드 (하단) */}
      <SelectedAptCard
        data={selectedApt}
        loading={loadingApt}
        onClose={() => setSelectedApt(null)}
      />
    </SafeAreaView>
  );
}

/* ───────── UI SUBCOMPONENTS ───────── */
function ToolbarButton({
  label,
  onPress,
  active = false,
}: {
  label: string;
  onPress: () => void;
  active?: boolean;
}) {
  return (
    <TouchableOpacity
      style={[styles.btn, active && styles.btnActive]}
      onPress={onPress}
      activeOpacity={0.85}
    >
      <Text style={styles.btnText}>{label}</Text>
    </TouchableOpacity>
  );
}

function SummaryBar({ data }: { data: DailySummary }) {
  if (!data) return null;
  return (
    <View style={uxStyles.summaryBar}>
      <Text style={uxStyles.sumText}>
        매매가: {fmtWon(data.sale)} · 전세가: {fmtWon(data.rent)} · 거래량:{' '}
        {data.trades.toLocaleString()}건
      </Text>
    </View>
  );
}

function RankingCard({ visible }: { visible: boolean }) {
  if (!visible) return null;
  return (
    <View style={uxStyles.ranking}>
      <Text style={uxStyles.rankTitle}>랭킹 (DEMO)</Text>
      <Text style={uxStyles.rankSub}>차트/지표는 추후 연결</Text>
    </View>
  );
}

/** ✅ 하단에 뜨는 단지 기본정보 카드 */
function SelectedAptCard({
  data,
  loading,
  onClose,
}: {
  data: AptBasic | null;
  loading: boolean;
  onClose: () => void;
}) {
  if (!data && !loading) return null;

  return (
    <View style={aptCardStyles.wrap}>
      <View style={aptCardStyles.inner}>
        <View style={aptCardStyles.headerRow}>
          <Text style={aptCardStyles.title}>
            {loading ? '로딩 중...' : data?.apt_nm ?? '(단지명 없음)'}
          </Text>
          <TouchableOpacity onPress={onClose} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
            <Text style={aptCardStyles.close}>✕</Text>
          </TouchableOpacity>
        </View>

        {loading ? (
          <View style={aptCardStyles.loadingRow}>
            <ActivityIndicator />
          </View>
        ) : (
          <>
            <Text style={aptCardStyles.addr}>
              {data?.apt_rdn_addr ?? '주소 정보 없음'}
            </Text>

            <View style={aptCardStyles.row}>
              <Text style={aptCardStyles.key}>세대수</Text>
              <Text style={aptCardStyles.val}>
                {data?.tnohsh ?? '―'} 세대
              </Text>
            </View>

            <View style={aptCardStyles.row}>
              <Text style={aptCardStyles.key}>동 수</Text>
              <Text style={aptCardStyles.val}>
                {data?.whol_dong_cnt ?? '―'} 동
              </Text>
            </View>

            <View style={aptCardStyles.row}>
              <Text style={aptCardStyles.key}>사용승인일</Text>
              <Text style={aptCardStyles.val}>
                {data?.use_aprv_ymd ?? '―'}
              </Text>
            </View>

{/*}          <View style={aptCardStyles.row}>
              <Text style={aptCardStyles.key}>좌표</Text>
              <Text style={aptCardStyles.val}>
                {data?.lat ?? '―'}, {data?.lng ?? '―'}
              </Text>
            </View> */}
          </>
        )}
      </View>
    </View>
  );
}

/* ───────── STYLES ───────── */
const styles = StyleSheet.create({
  toolbar: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: TOOLBAR_H,
    paddingHorizontal: 8,
    gap: 8,
    backgroundColor: '#0b1220',
    flexDirection: 'row',
    alignItems: 'center',
    zIndex: 10,
    elevation: 10,
  },
  btn: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: '#243b80',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#334155',
  },
  btnActive: { backgroundColor: '#2f6fed' },
  btnText: { color: '#fff', fontWeight: '700' },

  searchWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    marginLeft: 6,
    gap: 6,
    flex: 1,
  },
  input: {
    flex: 1,
    height: 36,
    borderRadius: 8,
    paddingHorizontal: 10,
    backgroundColor: '#111827',
    color: '#fff',
    borderWidth: 1,
    borderColor: '#334155',
  },
  searchBtn: {
    paddingHorizontal: 12,
    height: 36,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#2f6fed',
  },
  searchBtnText: { color: '#fff', fontWeight: '700' },
});

const uxStyles = StyleSheet.create({
  summaryBar: {
    position: 'absolute',
    top: TOOLBAR_H + 38,
    left: 0,
    right: 0,
    paddingVertical: 6,
    paddingHorizontal: 10,
    backgroundColor: 'rgba(12,18,34,.88)',
    borderBottomWidth: 1,
    borderColor: '#1f2a44',
    zIndex: 9,
  },
  sumText: {
    color: '#e6eefc',
    textAlign: 'center',
    fontWeight: '700',
  },
  ranking: {
    position: 'absolute',
    top: TOOLBAR_H + 80,
    right: 10,
    width: 220,
    backgroundColor: 'rgba(12,18,34,.92)',
    borderRadius: 12,
    padding: 12,
    gap: 6,
    borderWidth: 1,
    borderColor: '#1f2a44',
    zIndex: 9,
  },
  rankTitle: { color: '#fff', fontWeight: '800' },
  rankSub: { color: '#cbd5e1' },
});

const periodStyles = StyleSheet.create({
  bar: {
    position: 'absolute',
    top: TOOLBAR_H,
    left: 0,
    right: 0,
    height: 38,
    backgroundColor: 'rgba(8,12,24,.9)',
    zIndex: 9,
    borderBottomWidth: 1,
    borderColor: '#1f2a44',
  },
  barContent: {
    paddingHorizontal: 8,
    alignItems: 'center',
    gap: 8,
  },
  pill: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 9999,
    borderWidth: 1,
    borderColor: '#334155',
    backgroundColor: '#0b1220',
  },
  pillActive: {
    backgroundColor: '#2f6fed',
    borderColor: '#2f6fed',
  },
  pillText: {
    color: '#cbd5e1',
    fontWeight: '700',
    fontSize: 12,
  },
  pillTextActive: { color: '#fff' },
});

const aptCardStyles = StyleSheet.create({
  wrap: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 20,
    paddingHorizontal: 12,
    zIndex: 20,
  },
  inner: {
    backgroundColor: 'rgba(12,18,34,.92)',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#1f2a44',
    padding: 12,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 6,
  },
  title: {
    color: '#fff',
    fontWeight: '800',
    fontSize: 16,
    flexShrink: 1,
    paddingRight: 8,
    lineHeight: 20,
  },
  close: {
    color: '#fff',
    fontWeight: '700',
    fontSize: 16,
  },
  addr: {
    color: '#cbd5e1',
    fontSize: 13,
    lineHeight: 18,
    marginBottom: 10,
  },
  row: {
    flexDirection: 'row',
    marginBottom: 4,
  },
  key: {
    width: 80,
    color: '#94a3b8',
    fontSize: 13,
    fontWeight: '600',
  },
  val: {
    flex: 1,
    color: '#fff',
    fontSize: 13,
    fontWeight: '600',
  },
  loadingRow: {
    paddingVertical: 12,
    alignItems: 'center',
  },
});

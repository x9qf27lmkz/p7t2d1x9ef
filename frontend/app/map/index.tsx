// app/map/index.tsx
import React from 'react';
import { StyleSheet, View } from 'react-native';
import MapView, { PROVIDER_GOOGLE, UrlTile, Marker } from 'react-native-maps';

const VWORLD_KEY = process.env.EXPO_PUBLIC_VWORLD_KEY!;

// vworld WMTS(슬리피 XYZ) 템플릿
// - Base: 기본지도, Midnight: 야간, Hybrid: 하이브리드(위성+라벨), Satellite: 위성
// - GoogleMapsCompatible 매트릭스 세트 사용
const VWORLD_URL =
  `https://api.vworld.kr/req/wmts/1.0.0/${VWORLD_KEY}/Base/{z}/{y}/{x}.png` +
  `?tileMatrixSet=GoogleMapsCompatible&format=image/png`;

export default function MapScreen() {
  return (
    <View style={styles.container}>
      <MapView
        provider={PROVIDER_GOOGLE}
        style={StyleSheet.absoluteFill}
        initialRegion={{
          latitude: 37.5665,     // 서울 중심
          longitude: 126.9780,
          latitudeDelta: 0.15,
          longitudeDelta: 0.15,
        }}
      >
        {/* vworld 타일 오버레이 */}
        <UrlTile
          urlTemplate={VWORLD_URL}
          maximumZ={19}      // vworld 권장 최대 줌
          tileSize={256}
          zIndex={0}
          opacity={1}
        />

        {/* 테스트 마커 */}
        <Marker
          coordinate={{ latitude: 37.5665, longitude: 126.9780 }}
          title="서울시청"
          description="vworld 타일이 보이면 성공!"
        />
      </MapView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
});

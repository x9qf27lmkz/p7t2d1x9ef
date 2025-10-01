import axios from 'axios';
import React, { useEffect, useState } from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import MapView, { Marker } from 'react-native-maps';

export default function ApartmentMap() {
  const [apartments, setApartments] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get('http://192.168.0.xxx:8000/apartments') // ← ⚠️ 여기 로컬 PC의 IP 주소로 교체!
      .then(res => {
        const withCoords = res.data.filter(a => a.x && a.y);
        setApartments(withCoords);
      })
      .catch(err => console.error('API fetch error:', err))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <ActivityIndicator size="large" color="#0000ff" style={{ flex: 1 }} />;
  }

  return (
    <View style={styles.container}>
      <MapView
        style={styles.map}
        initialRegion={{
          latitude: 37.6544,        // 노원구 중심
          longitude: 127.0568,
          latitudeDelta: 0.02,
          longitudeDelta: 0.02,
        }}
      >
        {apartments.map((apt) => (
          <Marker
            key={apt.id}
            coordinate={{ latitude: apt.y, longitude: apt.x }}
            title={apt.apt_name}
            description={apt.new_address || apt.old_address}
          />
        ))}
      </MapView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  map: { flex: 1 },
});

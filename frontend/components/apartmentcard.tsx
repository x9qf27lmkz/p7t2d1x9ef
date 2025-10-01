import { StyleSheet, Text, View } from 'react-native';

interface ApartmentCardProps {
  name: string;
  vacancyRate: number;
}

export default function ApartmentCard({ name, vacancyRate }: ApartmentCardProps) {
  return (
    <View style={styles.card}>
      <Text style={styles.name}>{name}</Text>
      <Text>공실률: {vacancyRate}%</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    padding: 16,
    marginVertical: 8,
    backgroundColor: '#f2f2f2',
    borderRadius: 8,
  },
  name: {
    fontWeight: 'bold',
    fontSize: 18,
    marginBottom: 4,
  },
});

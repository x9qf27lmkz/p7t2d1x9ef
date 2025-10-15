// app/(tabs)/index.tsx
import { useEffect, useState } from "react";
import { View, Text, ScrollView } from "react-native";
import api from "../../src/services/api";

export default function Home() {
  const [msg, setMsg] = useState("loading...");
  useEffect(() => {
    api.post("/snapshot/seoul/trade", { }, { params: { year: 2025, gu: "노원구" }})
      .then(() => api.get("/map/markers", { params: { gu: "노원구" }}))
      .then(r => setMsg(JSON.stringify(r.data).slice(0, 800) + " ..."))
      .catch(e => setMsg("ERR: " + e.message));
  }, []);
  return <ScrollView contentContainerStyle={{padding:16}}><Text>{msg}</Text></ScrollView>;
}

// services/api.ts
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://192.168.55.195:8000', // FastAPI 백엔드 주소로 수정
  timeout: 5000,
});

export default api;

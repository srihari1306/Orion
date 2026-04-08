import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  withCredentials: false,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('orion_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('orion_token');
      localStorage.removeItem('orion_user');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export default api;

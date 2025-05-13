// src/axios.js
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Добавляем access-token в каждый запрос
api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Обработка 401 — пробуем рефрешить токен и повторить запрос
api.interceptors.response.use(
  response => response,
  async error => {
    const original = error.config;

    // пропускаем, если это сам refresh или уже ретраился
    if (error.response?.status === 401 && !original._retry && !original.url.endsWith('/api/auth/refresh/')) {
      original._retry = true;
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const { data } = await api.post('/api/auth/refresh/', {
            refresh: refreshToken
          });
          // сохраняем новый access (и, если есть, refresh)
          localStorage.setItem('access_token', data.access);
          if (data.refresh) {
            localStorage.setItem('refresh_token', data.refresh);
          }
          // подставляем новый токен и повторяем оригинальный запрос
          original.headers.Authorization = `Bearer ${data.access}`;
          return api(original);
        } catch (refreshError) {
          // не удалось обновить — убираем токены и редиректим на логин
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
          return Promise.reject(refreshError);
        }
      }
    }

    return Promise.reject(error);
  }
);

export default api;

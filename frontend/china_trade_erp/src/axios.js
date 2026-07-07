import axios from 'axios';

const AUTH_SESSION_KEY = 'auth_session';

function getCookie(name) {
  return document.cookie
    .split('; ')
    .find(row => row.startsWith(`${name}=`))
    ?.split('=')[1];
}

function clearClientSession() {
  localStorage.removeItem(AUTH_SESSION_KEY);
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('current_user_profile');
}

const api = axios.create({
  baseURL: 'http://localhost:8000/',
  withCredentials: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(config => {
  const csrfToken = getCookie('csrftoken');
  const method = (config.method || 'get').toUpperCase();
  if (csrfToken && !['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(method)) {
    config.headers['X-CSRFToken'] = decodeURIComponent(csrfToken);
  }
  return config;
});

api.interceptors.response.use(
  response => response,
  async error => {
    const original = error.config;
    const url = original?.url || '';

    if (
      error.response?.status === 401 &&
      original &&
      !original._retry &&
      !url.endsWith('/api/auth/refresh/') &&
      !url.endsWith('/api/auth/login/')
    ) {
      original._retry = true;
      try {
        await api.post('/api/auth/refresh/', {});
        localStorage.setItem(AUTH_SESSION_KEY, '1');
        return api(original);
      } catch (refreshError) {
        clearClientSession();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export { AUTH_SESSION_KEY, clearClientSession };
export default api;

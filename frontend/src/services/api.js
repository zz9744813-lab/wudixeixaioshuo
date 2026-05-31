import axios from 'axios';

export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const getApiKey = () =>
  process.env.REACT_APP_API_KEY || localStorage.getItem('APP_API_KEY') || '';

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 min for long writes/analysis
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use(
  (config) => {
    const key = getApiKey();
    if (key) config.headers['X-API-Key'] = key;
    return config;
  },
  (error) => Promise.reject(error),
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    const data = error?.response?.data;
    const message =
      (typeof data === 'string' && data) ||
      data?.detail ||
      data?.message ||
      error.message ||
      '请求失败，请重试';
    if (typeof window !== 'undefined') {
      const ev = new CustomEvent('app:api-error', {
        detail: { status, message, url: error?.config?.url, method: error?.config?.method },
      });
      window.dispatchEvent(ev);
    }
    return Promise.reject(error);
  },
);

export const get = (url, config = {}) => api.get(url, config);
export const post = (url, data = {}, config = {}) => api.post(url, data, config);
export const put = (url, data = {}, config = {}) => api.put(url, data, config);
export const del = (url, config = {}) => api.delete(url, config);

export default api;

import axios from 'axios';

// P0-1: 运行时配置优先级：window.__APP_CONFIG__ > 构建时环境变量 > fallback
const runtimeConfig =
  typeof window !== 'undefined' ? window.__APP_CONFIG__ || {} : {};
export const API_BASE_URL =
  runtimeConfig.API_BASE_URL ||
  process.env.REACT_APP_API_URL ||
  '/api';

// P1-1: 统一 API 错误解析
export function getApiErrorMessage(error) {
  const data = error?.response?.data;
  return (
    data?.error?.message ||
    data?.error?.detail ||
    data?.detail?.message ||
    data?.detail ||
    data?.message ||
    error?.message ||
    '请求失败，请重试'
  );
}

// P0-1: 运行时 API Key 注入
const getApiKey = () =>
  runtimeConfig.APP_API_KEY ||
  process.env.REACT_APP_API_KEY ||
  localStorage.getItem('APP_API_KEY') ||
  '';

export const hasApiKey = () => Boolean(getApiKey());

export const getApiRuntimeInfo = () => ({
  apiBaseUrl: API_BASE_URL,
  hasApiKey: hasApiKey(),
});

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
    const message = getApiErrorMessage(error);
    if (typeof window !== 'undefined') {
      const ev = new CustomEvent('app:api-error', {
        detail: {
          status,
          message,
          url: error?.config?.url,
          method: error?.config?.method,
        },
      });
      window.dispatchEvent(ev);
    }
    return Promise.reject(error);
  },
);

// 兼容旧页面写法：api.del(...)
api.del = (url, config = {}) => api.delete(url, config);

export const get = (url, config = {}) => api.get(url, config);
export const post = (url, data = {}, config = {}) =>
  api.post(url, data, config);
export const put = (url, data = {}, config = {}) =>
  api.put(url, data, config);
export const del = (url, config = {}) => api.delete(url, config);

export default api;

import axios from 'axios';

export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const getApiKey = () =>
  process.env.REACT_APP_API_KEY || localStorage.getItem('APP_API_KEY') || '';

// 创建 axios 实例
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器 - 自动注入 X-API-Key
api.interceptors.request.use(
  (config) => {
    const key = getApiKey();
    if (key) {
      config.headers['X-API-Key'] = key;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器 - 统一错误处理
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      console.error('🔒 未授权: API Key 无效或缺失');
    }
    if (error.response?.status === 413) {
      console.error('📦 文件过大');
    }
    return Promise.reject(error);
  }
);

// 便捷方法
export const get = (url, config = {}) => api.get(url, config);
export const post = (url, data = {}, config = {}) => api.post(url, data, config);
export const put = (url, data = {}, config = {}) => api.put(url, data, config);
export const del = (url, config = {}) => api.delete(url, config);

// 导出原始axios实例供特殊需求
export default api;

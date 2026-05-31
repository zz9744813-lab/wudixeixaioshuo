import { useCallback, useEffect, useState } from 'react';
import api from '../services/api';

/**
 * useFetch Hook
 * 统一处理数据获取的加载、错误、重试状态
 *
 * @param {string} url - API 地址
 * @param {object} options - 配置选项
 * @param {boolean} options.auto - 是否自动加载（默认 true）
 * @param {*} options.initialData - 初始数据（默认 undefined，避免 null 导致的解构默认值不生效）
 *
 * @returns {object} { data, loading, error, reload }
 */
export function useFetch(url, options = {}) {
  const { auto = true, initialData = undefined } = options;

  const [state, setState] = useState({
    data: initialData,
    loading: auto,
    error: null,
  });

  const reload = useCallback(async () => {
    setState((current) => ({
      ...current,
      loading: true,
      error: null,
    }));

    try {
      const response = await api.get(url);
      setState({
        data: response.data ?? initialData,
        loading: false,
        error: null,
      });
    } catch (error) {
      const message =
        error?.response?.data?.detail ||
        error?.response?.data?.message ||
        error.message ||
        '请求失败，请重试';

      setState({
        data: initialData,
        loading: false,
        error: message,
      });
    }
  }, [url, initialData]);

  useEffect(() => {
    if (auto) {
      reload();
    }
  }, [auto, reload]);

  return {
    data: state.data,
    loading: state.loading,
    error: state.error,
    reload,
  };
}

export default useFetch;

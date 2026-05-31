import { useCallback, useEffect, useRef, useState } from 'react';
import api from '../services/api';

/**
 * useFetch Hook
 * 统一处理数据获取的加载、错误、重试状态
 *
 * 关键设计：
 * - initialData 通过 ref 存储，不参与 reload/useEffect 依赖；
 * - 避免对象/数组字面量导致 useEffect 重复请求循环。
 *
 * @param {string} url - API 地址
 * @param {object} options - 配置选项
 * @param {boolean} options.auto - 是否自动加载（默认 true）
 * @param {*} options.initialData - 初始数据
 * @returns {object} { data, loading, error, reload }
 */
export function useFetch(url, options = {}) {
  const { auto = true, initialData = undefined } = options;
  const initialDataRef = useRef(initialData);

  const [state, setState] = useState({
    data: initialDataRef.current,
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
        data: response.data ?? initialDataRef.current,
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
        data: initialDataRef.current,
        loading: false,
        error: message,
      });
    }
  }, [url]); // 仅 url 参与依赖；initialData 通过 ref 访问

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

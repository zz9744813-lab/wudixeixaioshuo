import { useEffect, useState, useCallback } from 'react';

/**
 * useTheme Hook
 * 管理主题模式：system / light / dark
 * 持久化到 localStorage
 * system 模式下自动跟踪系统主题变化并应用 data-theme
 */
export function useTheme() {
  const [theme, setThemeState] = useState(() => {
    // 从 localStorage 读取，默认 system
    if (typeof window !== 'undefined') {
      return localStorage.getItem('theme') || 'system';
    }
    return 'system';
  });

  const setTheme = useCallback((newTheme) => {
    setThemeState(newTheme);
    if (typeof window !== 'undefined') {
      localStorage.setItem('theme', newTheme);
    }
  }, []);

  // 计算实际应应用的 data-theme 值
  useEffect(() => {
    const root = document.documentElement;

    if (theme === 'system') {
      // system 模式：根据系统偏好动态设置 data-theme
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      root.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
    } else {
      root.setAttribute('data-theme', theme);
    }
  }, [theme]);

  // 监听系统主题变化（system 模式下实时切换）
  useEffect(() => {
    if (theme !== 'system') return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    const handleChange = (e) => {
      // system 模式下，系统主题变化时更新 data-theme
      const root = document.documentElement;
      root.setAttribute('data-theme', e.matches ? 'dark' : 'light');
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [theme]);

  // 计算 isDark：供组件做条件样式判断
  const [isDark, setIsDark] = useState(() => {
    if (typeof window === 'undefined') return true;
    const saved = localStorage.getItem('theme') || 'system';
    if (saved === 'dark') return true;
    if (saved === 'light') return false;
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    if (theme === 'dark') {
      setIsDark(true);
    } else if (theme === 'light') {
      setIsDark(false);
    } else {
      // system: 跟踪系统偏好
      setIsDark(window.matchMedia('(prefers-color-scheme: dark)').matches);
    }
  }, [theme]);

  return {
    theme,
    setTheme,
    isDark,
  };
}

export default useTheme;
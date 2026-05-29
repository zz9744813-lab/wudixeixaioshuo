import { useEffect, useState, useCallback } from 'react';

/**
 * useTheme Hook
 * 管理主题模式：system / light / dark
 * 持久化到 localStorage
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

  useEffect(() => {
    const root = document.documentElement;

    if (theme === 'system') {
      root.removeAttribute('data-theme');
    } else {
      root.setAttribute('data-theme', theme);
    }
  }, [theme]);

  // 监听系统主题变化（当处于 system 模式时）
  useEffect(() => {
    if (theme !== 'system') return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    const handleChange = () => {
      // system 模式下，data-theme 属性已移除，由 CSS media query 控制
      // 不需要额外操作
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [theme]);

  return {
    theme,
    setTheme,
    isDark: theme === 'dark' ||
      (theme === 'system' &&
        typeof window !== 'undefined' &&
        window.matchMedia('(prefers-color-scheme: dark)').matches),
  };
}

export default useTheme;

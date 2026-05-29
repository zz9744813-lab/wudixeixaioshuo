import React from 'react';
import { Sun, Moon, Monitor } from 'lucide-react';
import { useTheme } from '../hooks/useTheme';
import './ThemeSwitcher.css';

/**
 * ThemeSwitcher 主题切换器
 * 支持 system / light / dark 三态切换
 */
export function ThemeSwitcher({ className = '' }) {
  const { theme, setTheme } = useTheme();

  const options = [
    { key: 'system', label: '自动', icon: Monitor },
    { key: 'light', label: '浅色', icon: Sun },
    { key: 'dark', label: '暗色', icon: Moon },
  ];

  return (
    <div className={`theme-switcher ${className}`}>
      {options.map(({ key, label, icon: Icon }) => (
        <button
          key={key}
          className={`theme-switcher__btn ${theme === key ? 'active' : ''}`}
          onClick={() => setTheme(key)}
          title={label}
          aria-label={`切换到${label}模式`}
        >
          <Icon size={16} />
        </button>
      ))}
    </div>
  );
}

export default ThemeSwitcher;

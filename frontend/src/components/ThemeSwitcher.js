import React from 'react';
import { Sun, Moon, Monitor } from 'lucide-react';
import { useTheme } from '../hooks/useTheme';
import './ThemeSwitcher.css';

const THEME_OPTIONS = [
  { key: 'light', icon: Sun, label: '浅色' },
  { key: 'dark', icon: Moon, label: '深色' },
  { key: 'system', icon: Monitor, label: '跟随系统' },
];

function ThemeSwitcher() {
  const { theme, setTheme } = useTheme();

  return (
    <div className="theme-switcher" role="group" aria-label="主题切换">
      {THEME_OPTIONS.map(({ key, icon: Icon, label }) => (
        <button
          key={key}
          className={`theme-switcher__btn ${theme === key ? 'active' : ''}`}
          onClick={() => setTheme(key)}
          title={label}
          aria-label={label}
          aria-pressed={theme === key}
        >
          <Icon size={16} />
        </button>
      ))}
    </div>
  );
}

export default ThemeSwitcher;

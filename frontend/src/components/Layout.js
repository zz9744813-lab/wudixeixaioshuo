import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  BookOpen,
  Lightbulb,
  FolderKanban,
  Factory,
  Cpu,
  Bot,
  ListChecks,
  Settings2,
  FileText,
  BarChart3,
  MessageSquare,
  GitBranch,
  Download,
  Terminal,
  Key
} from 'lucide-react';
import ApiKeyModal from './ApiKeyModal';
import ThemeSwitcher from './ThemeSwitcher';
import './Layout.css';

const NAV_GROUPS = [
  {
    group: '创作',
    items: [
      { to: '/', label: '仪表盘', icon: LayoutDashboard },
      { to: '/books', label: '拆书学习', icon: BookOpen },
      { to: '/techniques', label: '技巧库', icon: Lightbulb },
      { to: '/projects', label: '小说项目', icon: FolderKanban },
      { to: '/export', label: '小说导出', icon: Download },
    ],
  },
  {
    group: '自动化',
    items: [
      { to: '/factory', label: '写作工厂', icon: Factory },
      { to: '/worker', label: '自动写作控制台', icon: Cpu },
      { to: '/agents', label: 'Agent 控制台', icon: Bot },
      { to: '/tasks', label: '任务队列', icon: ListChecks },
    ],
  },
  {
    group: '配置',
    items: [
      { to: '/models', label: '模型配置', icon: Settings2 },
      { to: '/prompts', label: 'Prompt 模板', icon: FileText },
    ],
  },
  {
    group: '观测',
    items: [
      { to: '/usage', label: '用量/成本', icon: BarChart3 },
      { to: '/feedback', label: '反馈中心', icon: MessageSquare },
      { to: '/evolution', label: 'Darwin 进化', icon: GitBranch },
      { to: '/logs', label: '系统日志', icon: Terminal },
    ],
  },
];

function Layout({ children }) {
  const location = useLocation();
  const [isApiKeyModalOpen, setIsApiKeyModalOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const isActive = (path) => location.pathname === path;

  return (
    <div className="layout">
      <button
        className="sidebar-toggle"
        onClick={() => setSidebarOpen(!sidebarOpen)}
        aria-label={sidebarOpen ? '收起菜单' : '展开菜单'}
      >
        <span></span>
        <span></span>
        <span></span>
      </button>

      <aside className={`sidebar ${sidebarOpen ? 'sidebar--open' : ''}`}>
        <div className="logo">
          <h1>小说 Agent</h1>
          <p>24小时自动写作工作台</p>
          <div className="logo-actions">
            <button
              className="api-key-btn"
              onClick={() => setIsApiKeyModalOpen(true)}
              title="设置 API Key"
            >
              <Key size={14} />
              <span>API Key</span>
            </button>
            <ThemeSwitcher />
          </div>
        </div>

        <nav className="nav">
          {NAV_GROUPS.map((group) => (
            <div key={group.group} className="nav-group">
              <div className="nav-group-label">{group.group}</div>
              {group.items.map((item) => {
                const Icon = item.icon;
                const active = isActive(item.to);
                return (
                  <Link
                    key={item.to}
                    to={item.to}
                    className={`nav-item ${active ? 'active' : ''}`}
                    onClick={() => setSidebarOpen(false)}
                  >
                    <Icon size={18} className="nav-icon" aria-hidden="true" />
                    <span className="nav-label">{item.label}</span>
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>
      </aside>

      {sidebarOpen && (
        <div
          className="sidebar-overlay"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <main className="main-content">
        {children}
      </main>

      <ApiKeyModal
        isOpen={isApiKeyModalOpen}
        onClose={() => setIsApiKeyModalOpen(false)}
      />
    </div>
  );
}

export default Layout;

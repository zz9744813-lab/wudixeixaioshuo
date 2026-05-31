import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Icon } from './ui/Icon';
import ApiKeyModal from './ApiKeyModal';
import ThemeSwitcher from './ThemeSwitcher';
import styles from './Layout.module.css';

const NAV_GROUPS = [
  {
    group: '创作',
    items: [
      { to: '/', label: '仪表盘', icon: 'LayoutDashboard' },
      { to: '/books', label: '拆书学习', icon: 'BookOpen' },
      { to: '/techniques', label: '技巧库', icon: 'Lightbulb' },
      { to: '/projects', label: '小说项目', icon: 'FolderKanban' },
    { to: '/reader-training', label: '真人训练营', icon: 'Users' },
      { to: '/export', label: '小说导出', icon: 'Download' },
    ],
  },
  {
    group: '自动化',
    items: [
      { to: '/factory', label: '写作工厂', icon: 'Factory' },
      { to: '/worker', label: '自动写作控制台', icon: 'Cpu' },
      { to: '/agents', label: 'Agent 控制台', icon: 'Bot' },
      { to: '/agent-orchestrator', label: '自主 Orchestrator', icon: 'Workflow' },
      { to: '/tasks', label: '任务队列', icon: 'ListChecks' },
    ],
  },
  {
    group: '配置',
    items: [
      { to: '/models', label: '模型配置', icon: 'Settings2' },
      { to: '/llm-routes', label: 'LLM 路由池', icon: 'Route' },
      { to: '/prompts', label: 'Prompt 模板', icon: 'FileText' },
    ],
  },
  {
    group: '观测',
    items: [
      { to: '/usage', label: '用量/成本', icon: 'BarChart3' },
      { to: '/feedback', label: '反馈中心', icon: 'MessageSquare' },
      { to: '/evolution', label: 'Darwin 进化', icon: 'GitBranch' },
      { to: '/logs', label: '系统日志', icon: 'Terminal' },
    ],
  },
];

function Layout({ children }) {
  const location = useLocation();
  const [isApiKeyModalOpen, setIsApiKeyModalOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const isActive = (path) => location.pathname === path;

  return (
    <div className={styles.layout}>
      <button
        type="button"
        className={styles.sidebarToggle}
        onClick={() => setSidebarOpen((v) => !v)}
        aria-label={sidebarOpen ? '收起菜单' : '展开菜单'}
      >
        <span />
        <span />
        <span />
      </button>

      {sidebarOpen && (
        <div
          className={styles.sidebarOverlay}
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside className={`${styles.sidebar} ${sidebarOpen ? styles.sidebarOpen : ''}`}>
        <div className={styles.logo}>
          <h1>小说 Agent</h1>
          <p>24小时自动写作工作台</p>
          <div className={styles.logoActions}>
            <button
              type="button"
              className={styles.apiKeyBtn}
              onClick={() => { setIsApiKeyModalOpen(true); setSidebarOpen(false); }}
              title="设置 API Key"
            >
              <Icon name="Key" size={14} />
              <span>API Key</span>
            </button>
            <ThemeSwitcher />
          </div>
        </div>

        <nav className={styles.nav}>
          {NAV_GROUPS.map((group) => (
            <div key={group.group} className={styles.navGroup}>
              <div className={styles.navGroupLabel}>{group.group}</div>
              {group.items.map((item) => (
                <Link
                  key={item.to}
                  to={item.to}
                  className={`${styles.navItem} ${isActive(item.to) ? styles.active : ''}`}
                  onClick={() => setSidebarOpen(false)}
                >
                  <Icon name={item.icon} size={16} className={styles.navIcon} aria-hidden="true" />
                  <span className={styles.navLabel}>{item.label}</span>
                </Link>
              ))}
            </div>
          ))}
        </nav>
      </aside>

      <main className={styles.mainContent}>{children}</main>

      <ApiKeyModal
        isOpen={isApiKeyModalOpen}
        onClose={() => setIsApiKeyModalOpen(false)}
      />
    </div>
  );
}

export default Layout;

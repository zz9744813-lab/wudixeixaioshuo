import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import './Layout.css';

function Layout({ children }) {
  const location = useLocation();

  const menuItems = [
    { path: '/', label: '首页 Dashboard', icon: '📊' },
    { path: '/books', label: '拆书学习', icon: '📚' },
    { path: '/techniques', label: '技巧库', icon: '🎯' },
    { path: '/projects', label: '小说项目', icon: '📖' },
    { path: '/factory', label: '24小时写作工厂', icon: '🏭' },
    { path: '/agents', label: 'Agent 控制台', icon: '🤖' },
    { path: '/tasks', label: '任务队列', icon: '📋' },
    { path: '/models', label: '模型配置中心', icon: '⚙️' },
    { path: '/feedback', label: '反馈中心', icon: '💬' },
    { path: '/evolution', label: '失败模式库', icon: '📉' },
    { path: '/logs', label: '系统日志', icon: '📝' },
  ];

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="logo">
          <h1>🎭 小说 Agent</h1>
          <p>24小时自动写作工作台</p>
        </div>
        <nav className="nav">
          {menuItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`nav-item ${location.pathname === item.path ? 'active' : ''}`}
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </Link>
          ))}
        </nav>
      </aside>
      <main className="main-content">
        {children}
      </main>
    </div>
  );
}

export default Layout;

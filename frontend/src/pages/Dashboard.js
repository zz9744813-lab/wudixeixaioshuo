import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import './Dashboard.css';

function Dashboard() {
  const [stats, setStats] = useState(null);
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
    fetchActivities();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await api.get('/dashboard/stats');
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const fetchActivities = async () => {
    try {
      const response = await api.get('/dashboard/recent-activity');
      setActivities(response.data.activities);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching activities:', error);
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="loading">加载中...</div>;
  }

  return (
    <div className="dashboard">
      <header className="page-header">
        <h1>📊 仪表盘</h1>
        <p>欢迎来到 24小时小说 Agent 工作台</p>
      </header>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon">📖</div>
          <div className="stat-content">
            <h3>项目</h3>
            <div className="stat-value">{stats?.projects?.total || 0}</div>
            <div className="stat-detail">
              <span className="active">进行中: {stats?.projects?.active || 0}</span>
              <span>已完成: {stats?.projects?.completed || 0}</span>
            </div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">✍️</div>
          <div className="stat-content">
            <h3>章节</h3>
            <div className="stat-value">{stats?.chapters?.total || 0}</div>
            <div className="stat-detail">
              <span>已完成: {stats?.chapters?.completed || 0}</span>
            </div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">📝</div>
          <div className="stat-content">
            <h3>总字数</h3>
            <div className="stat-value">{(stats?.chapters?.total_words || 0).toLocaleString()}</div>
            <div className="stat-detail">
              <span>今日: {(stats?.chapters?.today_words || 0).toLocaleString()}</span>
            </div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">🤖</div>
          <div className="stat-content">
            <h3>任务</h3>
            <div className="stat-value">{stats?.tasks?.total || 0}</div>
            <div className="stat-detail">
              <span className="running">运行中: {stats?.tasks?.running || 0}</span>
              <span>待处理: {stats?.tasks?.pending || 0}</span>
            </div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">📚</div>
          <div className="stat-content">
            <h3>已拆书籍</h3>
            <div className="stat-value">{stats?.books?.total || 0}</div>
            <div className="stat-detail">
              <span>已分析: {stats?.books?.analyzed || 0}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="dashboard-sections">
        <div className="section">
          <h2>🚀 快速开始</h2>
          <div className="quick-actions">
            <Link to="/projects/new" className="action-card">
              <span className="action-icon">➕</span>
              <span>新建项目</span>
            </Link>
            <Link to="/books" className="action-card">
              <span className="action-icon">📤</span>
              <span>上传书籍</span>
            </Link>
            <Link to="/factory" className="action-card">
              <span className="action-icon">▶️</span>
              <span>启动写作</span>
            </Link>
            <Link to="/agents" className="action-card">
              <span className="action-icon">👁️</span>
              <span>查看 Agent</span>
            </Link>
          </div>
        </div>

        <div className="section">
          <h2>📋 最近活动</h2>
          <div className="activity-list">
            {activities.length === 0 ? (
              <p className="empty">暂无活动</p>
            ) : (
              activities.map((activity) => (
                <div key={activity.id} className="activity-item">
                  <span className={`activity-type ${activity.type}`}>
                    {activity.type}
                  </span>
                  <span className="activity-status">{activity.status}</span>
                  <span className="activity-time">
                    {new Date(activity.created_at).toLocaleString()}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;

import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import './Dashboard.css';
import {
  LayoutDashboard, FolderKanban, FileText, Bot, BookOpenText,
  Plus, Upload, Play, Eye, BookOpen,
} from 'lucide-react';

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
        <h1><LayoutDashboard size={18}/> 仪表盘</h1>
        <p>欢迎来到 24小时小说 Agent 工作台</p>
      </header>

      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-card__label"><BookOpen size={14} strokeWidth={1.75} /> 项目</div>
          <div className="stat-card__value num">{stats?.projects?.total || 0}</div>
          <div className="stat-card__detail num">进行中 {stats?.projects?.active || 0} · 已完成 {stats?.projects?.completed || 0}</div>
        </div>

        <div className="stat-card">
          <div className="stat-card__label"><FileText size={14} strokeWidth={1.75} /> 章节</div>
          <div className="stat-card__value num">{stats?.chapters?.total || 0}</div>
          <div className="stat-card__detail num">已完成 {stats?.chapters?.completed || 0}</div>
        </div>

        <div className="stat-card">
          <div className="stat-card__label"><FileText size={14} strokeWidth={1.75} /> 总字数</div>
          <div className="stat-card__value num">{(stats?.chapters?.total_words || 0).toLocaleString()}</div>
          <div className="stat-card__detail num">今日 {(stats?.chapters?.today_words || 0).toLocaleString()}</div>
        </div>

        <div className="stat-card">
          <div className="stat-card__label"><Bot size={14} strokeWidth={1.75} /> 任务</div>
          <div className="stat-card__value num">{stats?.tasks?.total || 0}</div>
          <div className="stat-card__detail num">运行中 {stats?.tasks?.running || 0} · 待处理 {stats?.tasks?.pending || 0}</div>
        </div>

        <div className="stat-card">
          <div className="stat-card__label"><BookOpenText size={14} strokeWidth={1.75} /> 已拆书籍</div>
          <div className="stat-card__value num">{stats?.books?.total || 0}</div>
          <div className="stat-card__detail num">已分析 {stats?.books?.analyzed || 0}</div>
        </div>
      </div>

      <div className="dashboard-sections">
        <div className="section">
          <h2> 快速开始</h2>
          <div className="quick-actions">
            <Link to="/projects/new" className="action-card">
              <span className="action-icon"><Plus size={16}/></span>
              <span>新建项目</span>
            </Link>
            <Link to="/books" className="action-card">
              <span className="action-icon"></span>
              <span>上传书籍</span>
            </Link>
            <Link to="/factory" className="action-card">
              <span className="action-icon"><Play size={16}/></span>
              <span>启动写作</span>
            </Link>
            <Link to="/agents" className="action-card">
              <span className="action-icon"><Eye size={16}/></span>
              <span>查看 Agent</span>
            </Link>
          </div>
        </div>

        <div className="section">
          <h2> 最近活动</h2>
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

import React, { useState, useEffect } from 'react';
import api from '../services/api';
import './FeedbackCenter.css';

const categoryLabels = {
  content: '内容',
  style: '风格',
  grammar: '语法',
  continuity: '连贯性',
  engagement: '吸引力',
};

const severityLabels = {
  low: '低',
  medium: '中',
  high: '高',
  critical: '严重',
};

function FeedbackCenter() {
  const [activeTab, setActiveTab] = useState('overview');
  const [feedbacks, setFeedbacks] = useState([]);
  const [stats, setStats] = useState(null);
  const [issues, setIssues] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [newFeedback, setNewFeedback] = useState({
    project_id: 1,
    category: 'content',
    severity: 'medium',
    content: '',
  });

  const fetchData = async () => {
    setLoading(true);
    try {
      const [fbRes, statsRes, issuesRes] = await Promise.all([
        api.get('/feedback/?limit=50'),
        api.get('/feedback/stats/overview'),
        api.get('/feedback/issues/common?limit=10'),
      ]);

      setFeedbacks(fbRes.data.items || []);
      setStats(statsRes.data);
      setIssues(issuesRes.data.issues || []);
    } catch (err) {
      setError('获取数据失败: ' + err.message);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSubmitFeedback = async () => {
    try {
      await api.post('/feedback/', newFeedback);
      setDialogOpen(false);
      setNewFeedback({ ...newFeedback, content: '' });
      fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || '提交失败');
    }
  };

  const handleResolve = async (id) => {
    try {
      await api.post(`/feedback/${id}/resolve`, { resolution: '已手动解决' });
      fetchData();
    } catch (err) {
      setError('操作失败: ' + err.message);
    }
  };

  const renderStats = () => {
    if (!stats) return <div className="loading">加载中...</div>;

    return (
      <div className="stats-grid">
        <div className="stat-card">
          <h3>总反馈数</h3>
          <div className="stat-value">{stats.total}</div>
        </div>
        <div className="stat-card">
          <h3>已解决</h3>
          <div className="stat-value success">{stats.resolved}</div>
        </div>
        <div className="stat-card">
          <h3>待处理</h3>
          <div className="stat-value warning">{stats.unresolved}</div>
        </div>
        <div className="stat-card">
          <h3>解决率</h3>
          <div className="stat-value">{stats.resolution_rate}%</div>
        </div>

        <div className="section-card full-width">
          <h2>各维度平均分</h2>
          <div className="score-grid">
            {Object.entries(stats.average_scores || {}).map(([dim, score]) => (
              <div key={dim} className="score-item">
                <span className="score-label">{dim}</span>
                <span className={`score-value ${score >= 7 ? 'success' : score >= 5 ? 'warning' : 'danger'}`}>
                  {score}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  const renderFeedbackList = () => (
    <div className="section-card">
      <div className="section-header">
        <h2>反馈列表</h2>
        <button className="btn btn-primary" onClick={() => setDialogOpen(true)}>提交反馈</button>
      </div>
      <div className="feedback-list">
        {feedbacks.map((fb) => (
          <div key={fb.id} className="feedback-item">
            <div className="feedback-header">
              <span className="badge badge-primary">{categoryLabels[fb.category] || fb.category}</span>
              <span className={`badge badge-${fb.severity === 'critical' || fb.severity === 'high' ? 'danger' : fb.severity === 'medium' ? 'warning' : 'success'}`}>
                {severityLabels[fb.severity]}
              </span>
              {fb.is_resolved && <span className="badge badge-success">已解决</span>}
              {!fb.is_resolved && (
                <button className="btn btn-sm" onClick={() => handleResolve(fb.id)}>解决</button>
              )}
            </div>
            <p className="feedback-content">{fb.content}</p>
            <span className="feedback-time">{new Date(fb.created_at).toLocaleString()}</span>
          </div>
        ))}
      </div>
    </div>
  );

  const renderCommonIssues = () => (
    <div className="section-card">
      <h2>常见问题</h2>
      <div className="issues-list">
        {issues.map((issue, index) => (
          <div key={issue.id} className="issue-item">
            <span>{index + 1}. {issue.content}</span>
            <span className={`badge badge-${issue.severity === 'critical' || issue.severity === 'high' ? 'danger' : issue.severity === 'medium' ? 'warning' : 'success'}`}>
              {severityLabels[issue.severity]}
            </span>
            <span className="text-muted">类别: {categoryLabels[issue.category] || issue.category}</span>
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <div className="feedback-center">
      <h1 className="page-title">反馈中心</h1>

      {error && <div className="alert alert-error" onClick={() => setError(null)}>{error}</div>}

      <div className="tabs">
        <button className={`tab ${activeTab === 'overview' ? 'active' : ''}`} onClick={() => setActiveTab('overview')}>统计概览</button>
        <button className={`tab ${activeTab === 'list' ? 'active' : ''}`} onClick={() => setActiveTab('list')}>反馈列表</button>
        <button className={`tab ${activeTab === 'issues' ? 'active' : ''}`} onClick={() => setActiveTab('issues')}>常见问题</button>
      </div>

      {activeTab === 'overview' && renderStats()}
      {activeTab === 'list' && renderFeedbackList()}
      {activeTab === 'issues' && renderCommonIssues()}

      {dialogOpen && (
        <div className="modal-overlay" onClick={() => setDialogOpen(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h2>提交反馈</h2>
            <div className="form-group">
              <label>类别</label>
              <select
                value={newFeedback.category}
                onChange={(e) => setNewFeedback({ ...newFeedback, category: e.target.value })}
              >
                <option value="content">内容</option>
                <option value="style">风格</option>
                <option value="grammar">语法</option>
                <option value="continuity">连贯性</option>
                <option value="engagement">吸引力</option>
              </select>
            </div>
            <div className="form-group">
              <label>严重程度</label>
              <select
                value={newFeedback.severity}
                onChange={(e) => setNewFeedback({ ...newFeedback, severity: e.target.value })}
              >
                <option value="low">低</option>
                <option value="medium">中</option>
                <option value="high">高</option>
                <option value="critical">严重</option>
              </select>
            </div>
            <div className="form-group">
              <label>反馈内容</label>
              <textarea
                rows={4}
                value={newFeedback.content}
                onChange={(e) => setNewFeedback({ ...newFeedback, content: e.target.value })}
              />
            </div>
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setDialogOpen(false)}>取消</button>
              <button className="btn btn-primary" onClick={handleSubmitFeedback}>提交</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default FeedbackCenter;

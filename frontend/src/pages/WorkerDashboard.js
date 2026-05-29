import React, { useState, useEffect } from 'react';
import api from '../services/api';
import './WorkerDashboard.css';

const statusMap = {
  idle: { label: '空闲', class: 'muted' },
  running: { label: '运行中', class: 'success' },
  paused: { label: '已暂停', class: 'warning' },
  stopped: { label: '已停止', class: 'danger' },
};

function WorkerDashboard() {
  const [workerStatus, setWorkerStatus] = useState(null);
  const [queueStatus, setQueueStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchStatus = async () => {
    try {
      const [workerRes, queueRes] = await Promise.all([
        api.get('/worker/stats'),
        api.get('/worker/queue/status'),
      ]);

      setWorkerStatus(workerRes.data.worker);
      setQueueStatus(queueRes.data);
    } catch (err) {
      setError('获取状态失败: ' + err.message);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const controlWorker = async (action) => {
    setLoading(true);
    try {
      const res = await api.post('/worker/control', { action });
      const data = res.data;
      setWorkerStatus((prev) => ({ ...prev, status: data.status }));
    } catch (err) {
      setError('操作失败: ' + err.message);
    }
    setLoading(false);
  };

  const resetStats = async () => {
    try {
      await api.post('/worker/reset-stats');
      fetchStatus();
    } catch (err) {
      setError('重置失败: ' + err.message);
    }
  };

  const formatTime = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return `${hours}小时 ${mins}分钟`;
  };

  const getStatusBadge = (status) => {
    const config = statusMap[status] || statusMap.idle;
    return <span className={`badge badge-${config.class}`}>{config.label}</span>;
  };

  if (!workerStatus || !queueStatus) {
    return <div className="loading">加载中...</div>;
  }

  const progress = queueStatus.progress || { percentage: 0, completed: 0, total: 0 };

  return (
    <div className="worker-dashboard">
      <h1 className="page-title">24小时自动写作控制台</h1>

      {error && <div className="alert alert-error" onClick={() => setError(null)}>{error}</div>}

      <div className="stats-grid">
        <div className="stat-card">
          <h3>Worker 状态</h3>
          <div className="stat-value">{getStatusBadge(workerStatus.status)}</div>
          <div className="worker-actions" style={{ marginTop: '12px' }}>
            {workerStatus.status === 'stopped' ? (
              <button className="btn btn-primary" onClick={() => controlWorker('start')} disabled={loading}>
                启动
              </button>
            ) : (
              <>
                <button className="btn btn-danger" onClick={() => controlWorker('stop')} disabled={loading}>
                  停止
                </button>
                {workerStatus.status === 'running' ? (
                  <button className="btn btn-secondary" onClick={() => controlWorker('pause')} disabled={loading}>
                    暂停
                  </button>
                ) : (
                  <button className="btn btn-secondary" onClick={() => controlWorker('resume')} disabled={loading}>
                    恢复
                  </button>
                )}
              </>
            )}
          </div>
          {workerStatus.current_task && (
            <div className="alert alert-info" style={{ marginTop: '12px' }}>
              正在写作: {workerStatus.current_task.chapter_title}
            </div>
          )}
        </div>

        <div className="stat-card">
          <h3>今日统计</h3>
          <div className="stat-item">
            <span>已完成章节</span>
            <span className="stat-value">{workerStatus.daily_stats?.chapters_completed || 0}</span>
          </div>
          <div className="stat-item">
            <span>已写字数</span>
            <span className="stat-value">{(workerStatus.daily_stats?.words_written || 0).toLocaleString()}</span>
          </div>
          <div className="stat-item">
            <span>Token 消耗</span>
            <span className="stat-value">{(workerStatus.daily_stats?.tokens_used || 0).toLocaleString()}</span>
          </div>
          <div className="stat-item">
            <span>运行时间</span>
            <span>{formatTime(workerStatus.uptime || 0)}</span>
          </div>
          <button className="btn btn-sm btn-secondary" onClick={resetStats} style={{ marginTop: '8px' }}>
            重置统计
          </button>
        </div>

        <div className="stat-card">
          <h3>写作队列</h3>
          <div className="progress-bar" style={{ marginBottom: '12px' }}>
            <div className="progress-fill" style={{ width: `${progress.percentage}%` }}></div>
          </div>
          <div className="progress-text">
            {progress.completed} / {progress.total} ({progress.percentage.toFixed(1)}%)
          </div>
          <div className="queue-stats">
            <div className="queue-item">
              <span>待写作</span>
              <span>{queueStatus.pending || 0}</span>
            </div>
            <div className="queue-item">
              <span>写作中</span>
              <span>{queueStatus.writing || 0}</span>
            </div>
            <div className="queue-item">
              <span>审核中</span>
              <span>{queueStatus.review || 0}</span>
            </div>
            <div className="queue-item">
              <span>已完成</span>
              <span>{queueStatus.completed || 0}</span>
            </div>
            <div className="queue-item">
              <span>失败</span>
              <span>{queueStatus.failed || 0}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="section-card">
        <h2>使用说明</h2>
        <p>1. 点击"启动"开始 24 小时自动写作循环</p>
        <p>2. Worker 会自动从队列中获取待写作章节</p>
        <p>3. 完成一章后自动开始下一章</p>
        <p>4. 达到每日字数或 Token 预算后自动暂停</p>
        <p>5. 可以在项目设置中配置每日目标</p>
      </div>
    </div>
  );
}

export default WorkerDashboard;

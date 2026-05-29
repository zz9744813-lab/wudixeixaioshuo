import React, { useState, useEffect } from 'react';
import api from '../services/api';
import './EvolutionCenter.css';

const statusLabels = {
  evaluating: '评估中',
  testing: '测试中',
  completed: '已完成',
  rolled_back: '已回滚',
};

function EvolutionCenter() {
  const [evolutions, setEvolutions] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [evoRes, statsRes] = await Promise.all([
        api.get("/evolution/"),
        api.get("/evolution/stats/overview"),
      ]);

      setEvolutions(evoRes.data.items || []);
      setStats(statsRes.data);
    } catch (err) {
      setError('获取数据失败: ' + err.message);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchData();
  }, []);

  const getStatusBadge = (status) => {
    const statusMap = {
      evaluating: { class: 'warning', label: '评估中' },
      testing: { class: 'warning', label: '测试中' },
      completed: { class: 'success', label: '已完成' },
      rolled_back: { class: 'danger', label: '已回滚' },
    };
    const config = statusMap[status] || { class: 'muted', label: status };
    return <span className={`badge badge-${config.class}`}>{config.label}</span>;
  };

  return (
    <div className="evolution-center">
      <h1 className="page-title">Darwin 进化中心</h1>

      {error && <div className="alert alert-error" onClick={() => setError(null)}>{error}</div>}

      {loading && <div className="loading">加载中...</div>}

      {stats && (
        <div className="stats-grid">
          <div className="stat-card">
            <h3>总进化轮次</h3>
            <div className="stat-value">{stats.total_evolutions || 0}</div>
          </div>
          <div className="stat-card">
            <h3>成功应用</h3>
            <div className="stat-value success">{stats.completed || 0}</div>
          </div>
          <div className="stat-card">
            <h3>已回滚</h3>
            <div className="stat-value danger">{stats.rolled_back || 0}</div>
          </div>
          <div className="stat-card">
            <h3>成功率</h3>
            <div className="stat-value">{stats.success_rate || 0}%</div>
          </div>
        </div>
      )}

      <div className="section-card">
        <div className="section-header">
          <h2>进化记录</h2>
          <button className="btn btn-primary" onClick={fetchData} disabled={loading}>
            刷新
          </button>
        </div>

        {evolutions.length === 0 ? (
          <p className="empty-text">暂无进化记录</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>目标维度</th>
                <th>策略</th>
                <th>状态</th>
                <th>创建时间</th>
              </tr>
            </thead>
            <tbody>
              {evolutions.map((evo) => (
                <tr key={evo.id}>
                  <td>{evo.id}</td>
                  <td>{evo.target_dimension}</td>
                  <td>{evo.strategy}</td>
                  <td>{getStatusBadge(evo.status)}</td>
                  <td>{new Date(evo.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export default EvolutionCenter;

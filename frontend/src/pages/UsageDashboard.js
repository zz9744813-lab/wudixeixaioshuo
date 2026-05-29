import React, { useEffect, useState } from 'react';
import api from '../services/api';

function UsageDashboard() {
  const [summary, setSummary] = useState(null);
  const [byRole, setByRole] = useState([]);
  const [byModel, setByModel] = useState([]);
  const [daily, setDaily] = useState([]);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(7);

  useEffect(() => {
    fetchData();
  }, [days]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [summaryRes, roleRes, modelRes, dailyRes] = await Promise.all([
        api.get("/usage/summary?days=${days}`),
        api.get("/usage/by-role?days=${days}`),
        api.get("/usage/by-model?days=${days}`),
        api.get("/usage/daily?days=${days}`),
      ]);

      setSummary(await summaryRes.json());
      setByRole(await roleRes.json());
      setByModel(await modelRes.json());
      setDaily(await dailyRes.json());
    } catch (error) {
      console.error('Error fetching usage data:', error);
    }
    setLoading(false);
  };

  if (loading) {
    return <div className="loading">加载中...</div>;
  }

  return (
    <div className="usage-dashboard">
      <header className="page-header">
        <h1>用量与成本看板</h1>
        <div className="days-selector">
          <label>时间范围：</label>
          <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
            <option value={7}>最近7天</option>
            <option value={30}>最近30天</option>
            <option value={90}>最近90天</option>
          </select>
        </div>
      </header>

      {/* 总览卡片 */}
      {summary && (
        <div className="stats-grid">
          <div className="stat-card">
            <h3>总调用次数</h3>
            <div className="stat-value">{summary.total_calls}</div>
            <div className="stat-detail">
              成功: {summary.success_calls} | 失败: {summary.failed_calls}
            </div>
          </div>
          <div className="stat-card">
            <h3>总Token数</h3>
            <div className="stat-value">{summary.total_tokens?.toLocaleString()}</div>
            <div className="stat-detail">
              输入: {summary.input_tokens?.toLocaleString()} | 输出: {summary.output_tokens?.toLocaleString()}
            </div>
          </div>
          <div className="stat-card">
            <h3>估算成本</h3>
            <div className="stat-value">${summary.estimated_cost?.toFixed(4)}</div>
            <div className="stat-detail">USD</div>
          </div>
        </div>
      )}

      {/* 按角色统计 */}
      <section className="usage-section">
        <h2>按角色统计</h2>
        <table className="data-table">
          <thead>
            <tr>
              <th>角色</th>
              <th>调用次数</th>
              <th>总Token数</th>
              <th>估算成本</th>
            </tr>
          </thead>
          <tbody>
            {byRole.map((item) => (
              <tr key={item.role}>
                <td>{item.role}</td>
                <td>{item.calls}</td>
                <td>{item.total_tokens?.toLocaleString()}</td>
                <td>${item.estimated_cost?.toFixed(4)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* 按模型统计 */}
      <section className="usage-section">
        <h2>按模型统计</h2>
        <table className="data-table">
          <thead>
            <tr>
              <th>模型</th>
              <th>调用次数</th>
              <th>总Token数</th>
              <th>估算成本</th>
            </tr>
          </thead>
          <tbody>
            {byModel.map((item) => (
              <tr key={item.model_name}>
                <td>{item.model_name}</td>
                <td>{item.calls}</td>
                <td>{item.total_tokens?.toLocaleString()}</td>
                <td>${item.estimated_cost?.toFixed(4)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* 每日趋势 */}
      <section className="usage-section">
        <h2>每日趋势</h2>
        <table className="data-table">
          <thead>
            <tr>
              <th>日期</th>
              <th>调用次数</th>
              <th>总Token数</th>
              <th>估算成本</th>
            </tr>
          </thead>
          <tbody>
            {daily.map((item) => (
              <tr key={item.date}>
                <td>{item.date}</td>
                <td>{item.calls}</td>
                <td>{item.total_tokens?.toLocaleString()}</td>
                <td>${item.estimated_cost?.toFixed(4)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

export default UsageDashboard;

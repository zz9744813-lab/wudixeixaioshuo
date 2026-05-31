import React, { useEffect, useState } from 'react';
import api, { getApiErrorMessage } from '../services/api';
import { toArray } from '../utils/nullSafety';
import './AgentOrchestratorPage.css';

function LLMRouterPage() {
  const [routes, setRoutes] = useState([]);
  const [providers, setProviders] = useState([]);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    provider_id: '',
    role: 'planner',
    priority: 100,
    weight: 1,
    enabled: true,
  });

  useEffect(() => {
    fetchAll();
  }, []);

  const fetchAll = async () => {
    try {
      const [routeResponse, providerResponse, statsResponse] = await Promise.all([
        api.get('/llm-routes'),
        api.get('/models/providers'),
        api.get('/llm-routes/stats/overview'),
      ]);
      setRoutes(routeResponse.data?.items || []);
      setProviders(providerResponse.data || []);
      setStats(statsResponse.data || null);
      setError('');
    } catch (err) {
      setError(err.response?.data?.detail || err.message || '加载 LLM 路由失败');
    }
  };

  const createRoute = async (event) => {
    event.preventDefault();
    try {
      await api.post('/llm-routes', {
        ...form,
        provider_id: Number(form.provider_id),
        priority: Number(form.priority),
        weight: Number(form.weight),
      });
      await fetchAll();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || '创建路由失败');
    }
  };

  const toggleRoute = async (route) => {
    try {
      await api.patch(`/llm-routes/${route.id}`, { enabled: !route.enabled });
      await fetchAll();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || '更新路由失败');
    }
  };

  return (
    <div className="agent-orchestrator-page">
      <header className="page-header">
        <div>
          <h1>LLM 路由池</h1>
          <p>按角色配置 provider 优先级、权重、fallback 与熔断统计。</p>
        </div>
      </header>

      {error && <div className="error-message">{error}</div>}

      <section className="status-grid">
        <div className="metric-card"><span>总调用</span><strong>{stats?.overall_total_calls || 0}</strong></div>
        <div className="metric-card"><span>总成本</span><strong>${stats?.overall_total_cost || 0}</strong></div>
        <div className="metric-card"><span>路由数</span><strong>{routes.length}</strong></div>
      </section>

      <form className="orchestrator-card" onSubmit={createRoute}>
        <h2>新增路由</h2>
        <div className="form-grid">
          <label>
            Provider
            <select
              value={form.provider_id}
              onChange={(event) => setForm({ ...form, provider_id: event.target.value })}
              required
            >
              <option value="">请选择</option>
              {providers.map((provider) => (
                <option key={provider.id} value={provider.id}>{provider.name} · {provider.default_model}</option>
              ))}
            </select>
          </label>
          <label>
            角色
            <input value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value })} required />
          </label>
          <label>
            优先级
            <input type="number" value={form.priority} onChange={(event) => setForm({ ...form, priority: event.target.value })} />
          </label>
          <label>
            权重
            <input type="number" min="1" value={form.weight} onChange={(event) => setForm({ ...form, weight: event.target.value })} />
          </label>
        </div>
        <button type="submit" className="btn-primary">保存路由</button>
      </form>

      <section className="orchestrator-card">
        <div className="section-title">
          <h2>路由配置</h2>
          <button type="button" className="btn-secondary" onClick={fetchAll}>刷新</button>
        </div>
        <div className="step-list">
          {routes.map((route) => (
            <div key={route.id} className="step-item">
              <div>
                <strong>{route.role}</strong>
                <p>{route.provider_name} · {route.default_model}</p>
                <p>优先级 {route.priority} · 权重 {route.weight} · 成功 {route.success_calls || 0}/{route.total_calls || 0}</p>
              </div>
              <button type="button" className="btn-secondary" onClick={() => toggleRoute(route)}>
                {route.enabled ? '禁用' : '启用'}
              </button>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

export default LLMRouterPage;

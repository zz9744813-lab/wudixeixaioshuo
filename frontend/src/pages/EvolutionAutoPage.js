import React, { useEffect, useState } from 'react';
import api from '../services/api';
import './AgentOrchestratorPage.css';

const ROLES = ['draft', 'critic', 'rewrite', 'continuity'];

function EvolutionAutoPage() {
  const [policies, setPolicies] = useState([]);
  const [runs, setRuns] = useState([]);
  const [metrics, setMetrics] = useState({});
  const [newRole, setNewRole] = useState('draft');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchPolicies();
    fetchRuns();
  }, []);

  const fetchPolicies = async () => {
    try {
      const res = await api.get('/evolution-auto/policies');
      setPolicies(res.data || []);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  const fetchRuns = async () => {
    try {
      const res = await api.get('/evolution-auto/runs');
      setRuns(res.data || []);
    } catch (err) {
      console.error(err);
    }
  };

  const createPolicy = async () => {
    setLoading(true);
    setError('');
    try {
      await api.post('/evolution-auto/policies', {
        role: newRole,
        enabled: true,
        min_sample_count: 20,
        min_average_score: 80,
        max_rewrite_rate: 0.4,
        trigger_window_days: 7,
        candidate_count: 3,
        ab_test_sample_count: 10,
        min_improvement: 3.0,
        auto_apply: true,
        rollout_ratio: 0.2,
      });
      fetchPolicies();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const runEvolution = async (policyId) => {
    setLoading(true);
    setError('');
    try {
      await api.post(`/evolution-auto/policies/${policyId}/run`);
      fetchRuns();
      fetchPolicies();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const rollbackRun = async (runId) => {
    const reason = prompt('请输入回滚原因：');
    if (!reason) return;
    try {
      await api.post(`/evolution-auto/runs/${runId}/rollback`, { reason });
      fetchRuns();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  return (
    <div className="agent-orchestrator-page">
      <header className="page-header">
        <div>
          <h1>自治进化系统</h1>
          <p>监控质量指标，自动诊断、生成 Prompt 候选、A/B 验证、灰度上线。</p>
        </div>
      </header>

      <section className="orchestrator-card">
        <h2>创建进化策略</h2>
        <div className="form-grid">
          <label>
            角色
            <select value={newRole} onChange={e => setNewRole(e.target.value)}>
              {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
          </label>
          <div style={{ display: 'flex', alignItems: 'flex-end' }}>
            <button className="btn-primary" onClick={createPolicy} disabled={loading}>
              {loading ? '创建中...' : '创建策略'}
            </button>
          </div>
        </div>
      </section>

      {error && <div className="error-message">{error}</div>}

      <section className="orchestrator-card">
        <h2>进化策略</h2>
        <div className="run-list">
          {policies.length === 0 ? (
            <p className="empty-state">暂无进化策略。</p>
          ) : policies.map(p => (
            <div key={p.id} className="step-item">
              <div>
                <strong>{p.role}</strong>
                <p>
                  样本阈值: {p.min_sample_count} ·
                  最低分: {p.min_average_score} ·
                  重写率: {(p.max_rewrite_rate * 100).toFixed(0)}% ·
                  自动应用: {p.auto_apply ? '是' : '否'}
                </p>
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <span className={`status-pill ${p.enabled ? 'succeeded' : 'failed'}`}>
                  {p.enabled ? '启用' : '禁用'}
                </span>
                <button className="btn-secondary" onClick={() => runEvolution(p.id)} disabled={loading}>
                  执行进化
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="orchestrator-card">
        <h2>进化运行历史</h2>
        <div className="run-list">
          {runs.length === 0 ? (
            <p className="empty-state">暂无进化运行记录。</p>
          ) : runs.map(r => (
            <div key={r.id} className="step-item">
              <div>
                <strong>#{r.id} {r.role}</strong>
                <p>状态: {r.status}</p>
                {r.diagnosis && <p>诊断: {r.diagnosis}</p>}
                {r.candidate_prompts_json && (
                  <p>候选数: {r.candidate_prompts_json.length}</p>
                )}
                {r.ab_test_result_json && (
                  <p>改进幅度: {r.ab_test_result_json.improvement?.toFixed(1) || 'N/A'}</p>
                )}
                {r.error_message && <p className="error-text">{r.error_message}</p>}
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <span className={`status-pill ${r.status}`}>{r.status}</span>
                {r.status === 'applied' && (
                  <button className="btn-secondary" onClick={() => rollbackRun(r.id)}>
                    回滚
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

export default EvolutionAutoPage;

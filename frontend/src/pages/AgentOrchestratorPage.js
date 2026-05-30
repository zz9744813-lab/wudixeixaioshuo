import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import './AgentOrchestratorPage.css';

const DEFAULT_REQUEST = '创建一部东方修仙系统流小说，面向起点读者，目标 200万字，日更 1 万。';

function AgentOrchestratorPage() {
  const [userRequest, setUserRequest] = useState(DEFAULT_REQUEST);
  const [mode, setMode] = useState('autonomous');
  const [maxSteps, setMaxSteps] = useState(30);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchRuns();
  }, []);

  const fetchRuns = async () => {
    try {
      const response = await api.get('/agent-runs');
      setRuns(response.data || []);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || '加载运行记录失败');
    }
  };

  const createRun = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const response = await api.post('/agent-runs', {
        user_request: userRequest,
        mode,
        max_steps: Number(maxSteps) || 30,
      });
      await api.post(`/agent-runs/${response.data.id}/start`);
      await fetchRuns();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || '创建运行失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="agent-orchestrator-page">
      <header className="page-header">
        <div>
          <h1>自主 Orchestrator</h1>
          <p>从用户需求生成可审计计划，并调用真实项目、Bible、章节与任务队列工具。</p>
        </div>
      </header>

      <form className="orchestrator-card" onSubmit={createRun}>
        <label>
          创作需求
          <textarea
            value={userRequest}
            onChange={(event) => setUserRequest(event.target.value)}
            rows={6}
            required
          />
        </label>
        <div className="form-grid">
          <label>
            运行模式
            <select value={mode} onChange={(event) => setMode(event.target.value)}>
              <option value="autonomous">自主执行</option>
              <option value="require_approval">先生成计划，等待确认</option>
            </select>
          </label>
          <label>
            最大步骤数
            <input
              type="number"
              min="1"
              max="100"
              value={maxSteps}
              onChange={(event) => setMaxSteps(event.target.value)}
            />
          </label>
        </div>
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? '正在创建...' : '创建并启动 Agent Run'}
        </button>
      </form>

      {error && <div className="error-message">{error}</div>}

      <section className="orchestrator-card">
        <div className="section-title">
          <h2>最近运行</h2>
          <button type="button" className="btn-secondary" onClick={fetchRuns}>刷新</button>
        </div>
        <div className="run-list">
          {runs.length === 0 ? (
            <p className="empty-state">暂无运行记录。</p>
          ) : (
            runs.map((run) => (
              <Link key={run.id} className="run-item" to={`/agent-runs/${run.id}`}>
                <div>
                  <strong>#{run.id}</strong>
                  <p>{run.user_request}</p>
                </div>
                <span className={`status-pill ${run.status}`}>{run.status}</span>
              </Link>
            ))
          )}
        </div>
      </section>
    </div>
  );
}

export default AgentOrchestratorPage;

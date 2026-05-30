import React, { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import api from '../services/api';
import './AgentOrchestratorPage.css';

function AgentRunDetailPage() {
  const { id } = useParams();
  const [run, setRun] = useState(null);
  const [subagents, setSubagents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchDetail = useCallback(async () => {
    try {
      const [runResponse, subagentResponse] = await Promise.all([
        api.get(`/agent-runs/${id}`),
        api.get('/subagents/tasks', { params: { run_id: id } }),
      ]);
      setRun(runResponse.data);
      setSubagents(subagentResponse.data || []);
      setError('');
    } catch (err) {
      setError(err.response?.data?.detail || err.message || '加载运行详情失败');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchDetail();
    const timer = setInterval(fetchDetail, 3000);
    return () => clearInterval(timer);
  }, [fetchDetail]);

  const cancelRun = async () => {
    try {
      await api.post(`/agent-runs/${id}/cancel`);
      fetchDetail();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || '取消失败');
    }
  };

  if (loading) return <div className="agent-orchestrator-page">加载中...</div>;
  if (error && !run) return <div className="agent-orchestrator-page error-message">{error}</div>;

  return (
    <div className="agent-orchestrator-page">
      <header className="page-header">
        <div>
          <Link to="/agent-orchestrator">← 返回 Orchestrator</Link>
          <h1>Agent Run #{run.id}</h1>
          <p>{run.user_request}</p>
        </div>
        <button type="button" className="btn-secondary" onClick={cancelRun}>取消运行</button>
      </header>

      {error && <div className="error-message">{error}</div>}

      <section className="status-grid">
        <div className="metric-card"><span>状态</span><strong>{run.status}</strong></div>
        <div className="metric-card"><span>模式</span><strong>{run.mode}</strong></div>
        <div className="metric-card"><span>项目 ID</span><strong>{run.project_id || '-'}</strong></div>
        <div className="metric-card"><span>最大步骤</span><strong>{run.max_steps}</strong></div>
      </section>

      <section className="orchestrator-card">
        <div className="section-title">
          <h2>执行步骤</h2>
          <button type="button" className="btn-secondary" onClick={fetchDetail}>刷新</button>
        </div>
        <div className="step-list">
          {(run.steps || []).map((step) => (
            <div key={step.id} className="step-item">
              <div>
                <strong>{step.title}</strong>
                <p>{step.step_key} · {step.tool_name}</p>
                {step.error_message && <p className="error-text">{step.error_message}</p>}
              </div>
              <span className={`status-pill ${step.status}`}>{step.status}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="orchestrator-card">
        <h2>子 Agent 任务</h2>
        <div className="step-list">
          {subagents.length === 0 ? (
            <p className="empty-state">暂无子 Agent 任务。</p>
          ) : subagents.map((task) => (
            <div key={task.id} className="step-item">
              <div>
                <strong>{task.title}</strong>
                <p>{task.role} · {task.task_type}</p>
                {task.output_text && <pre>{task.output_text}</pre>}
              </div>
              <span className={`status-pill ${task.status}`}>{task.status}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="orchestrator-card">
        <h2>最终报告</h2>
        {run.final_report ? <pre>{run.final_report}</pre> : <p className="empty-state">尚未生成最终报告。</p>}
      </section>
    </div>
  );
}

export default AgentRunDetailPage;

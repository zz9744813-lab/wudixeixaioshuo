import React, { useEffect, useState } from 'react';
import api from '../services/api';
import './AgentOrchestratorPage.css';

function ResearchAgentPage() {
  const [topic, setTopic] = useState('东方修仙 系统流');
  const [researchType, setResearchType] = useState('pattern');
  const [projectId, setProjectId] = useState('');
  const [runs, setRuns] = useState([]);
  const [patterns, setPatterns] = useState([]);
  const [insights, setInsights] = useState([]);
  const [trends, setTrends] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchRuns();
    fetchKnowledge();
  }, []);

  const fetchRuns = async () => {
    try {
      const res = await api.get('/research/runs');
      setRuns(res.data || []);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  const fetchKnowledge = async () => {
    try {
      const [pRes, iRes, tRes] = await Promise.all([
        api.get('/research/patterns'),
        api.get('/research/reader-insights'),
        api.get('/research/trends'),
      ]);
      setPatterns(pRes.data || []);
      setInsights(iRes.data || []);
      setTrends(tRes.data || []);
    } catch (err) {
      console.error(err);
    }
  };

  const startResearch = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await api.post('/research/runs', {
        topic,
        research_type: researchType,
        project_id: projectId ? Number(projectId) : null,
      });
      fetchRuns();
      fetchKnowledge();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const applyToProject = async (knowledgeType, ids) => {
    const pid = projectId ? Number(projectId) : null;
    if (!pid) {
      setError('请先填写项目 ID');
      return;
    }
    try {
      await api.post('/research/apply-to-project', {
        knowledge_type: knowledgeType,
        knowledge_ids: ids,
        project_id: pid,
        apply_to_bible: true,
      });
      alert('已应用到项目');
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  return (
    <div className="agent-orchestrator-page">
      <header className="page-header">
        <div>
          <h1>联网研究 Agent</h1>
          <p>搜索公开资料，抽取套路/评论/趋势/风格，沉淀到知识库。</p>
        </div>
      </header>

      <form className="orchestrator-card" onSubmit={startResearch}>
        <label>
          研究主题
          <input value={topic} onChange={e => setTopic(e.target.value)} required />
        </label>
        <div className="form-grid">
          <label>
            研究类型
            <select value={researchType} onChange={e => setResearchType(e.target.value)}>
              <option value="pattern">套路模式</option>
              <option value="comment">读者评论</option>
              <option value="trend">市场趋势</option>
              <option value="style">作者风格</option>
            </select>
          </label>
          <label>
            关联项目 ID（可选）
            <input type="number" value={projectId} onChange={e => setProjectId(e.target.value)} placeholder="留空则不关联" />
          </label>
        </div>
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? '研究中...' : '启动研究'}
        </button>
      </form>

      {error && <div className="error-message">{error}</div>}

      <section className="orchestrator-card">
        <h2>研究历史</h2>
        <div className="run-list">
          {runs.length === 0 ? (
            <p className="empty-state">暂无研究记录。</p>
          ) : runs.map(run => (
            <div key={run.id} className="run-item">
              <div>
                <strong>#{run.id} {run.topic}</strong>
                <p>{run.research_type} · {run.extracted_summary || '处理中...'}</p>
              </div>
              <span className={`status-pill ${run.status}`}>{run.status}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="orchestrator-card">
        <div className="section-title">
          <h2>知识模式库</h2>
          {projectId && (
            <button className="btn-secondary" onClick={() => applyToProject('pattern', patterns.map(p => p.id))}>
              全部应用到项目
            </button>
          )}
        </div>
        <div className="run-list">
          {patterns.length === 0 ? (
            <p className="empty-state">暂无知识模式。</p>
          ) : patterns.map(p => (
            <div key={p.id} className="step-item">
              <div>
                <strong>{p.pattern_name}</strong>
                <p>{p.pattern_type} · {p.genre || '通用'} · 置信度: {(p.confidence * 100).toFixed(0)}%</p>
                <p>{p.description}</p>
              </div>
              <span className="status-pill">{p.pattern_type}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="orchestrator-card">
        <h2>读者洞察</h2>
        <div className="run-list">
          {insights.length === 0 ? (
            <p className="empty-state">暂无读者洞察。</p>
          ) : insights.map(i => (
            <div key={i.id} className="step-item">
              <div>
                <strong>{i.title}</strong>
                <p>{i.insight_type} · 置信度: {(i.confidence * 100).toFixed(0)}%</p>
                <p>{i.description}</p>
              </div>
              <span className={`status-pill ${i.insight_type === 'drop' ? 'failed' : 'succeeded'}`}>
                {i.insight_type}
              </span>
            </div>
          ))}
        </div>
      </section>

      <section className="orchestrator-card">
        <h2>趋势报告</h2>
        <div className="run-list">
          {trends.length === 0 ? (
            <p className="empty-state">暂无趋势报告。</p>
          ) : trends.map(t => (
            <div key={t.id} className="step-item">
              <div>
                <strong>{t.report_title}</strong>
                <p>{t.genre || '通用'} · {t.platform || '综合'}</p>
                <p>{t.report_body}</p>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

export default ResearchAgentPage;

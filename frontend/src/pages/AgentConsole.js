import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../services/api';
import './AgentConsole.css';

function AgentConsole() {
  const [agentStatus, setAgentStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAgentStatus();
  }, []);

  const fetchAgentStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/agents/status`);
      const data = await response.json();
      setAgentStatus(data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching agent status:', error);
      setLoading(false);
    }
  };

  const handleGenerateChapter = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/agents/generate-chapter`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: 1, chapter_index: 1, title: '测试章节' }),
      });
      const data = await response.json();
      alert(`章节生成完成！得分: ${data.final_score}`);
    } catch (error) {
      console.error('Error generating chapter:', error);
    }
  };

  if (loading) {
    return <div className="loading">加载中...</div>;
  }

  return (
    <div className="agent-console">
      <header className="page-header">
        <h1>🤖 Agent 控制台</h1>
        <button className="btn-primary" onClick={handleGenerateChapter}>
          📝 生成测试章节
        </button>
      </header>

      <div className="console-layout">
        <div className="agent-list">
          <h3>Agent 状态</h3>
          <div className="status-summary">
            <div className={`status-badge ${agentStatus?.status}`}>
              {agentStatus?.status === 'running' ? '🟢 运行中' : '⚪ 空闲'}
            </div>
            <div className="task-count">
              <span>运行中: {agentStatus?.running_tasks || 0}</span>
              <span>待处理: {agentStatus?.pending_tasks || 0}</span>
            </div>
          </div>

          <div className="agents">
            {agentStatus?.agents?.map((agent) => (
              <div key={agent.name} className="agent-item">
                <div className="agent-info">
                  <span className="agent-name">{agent.name}</span>
                  <span className="agent-desc">{agent.description}</span>
                </div>
                <span className={`agent-status ${agent.status}`}>{agent.status}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="agent-workspace">
          <h3>工作区</h3>
          <p className="empty">选择任务查看详情</p>
        </div>

        <div className="agent-output">
          <h3>产物与版本</h3>
          <p className="empty">生成的内容将显示在这里</p>
        </div>
      </div>
    </div>
  );
}

export default AgentConsole;

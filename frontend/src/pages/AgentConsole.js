import React, { useState, useEffect, useRef } from 'react';
import api from '../services/api';
import { eventStream, subscribeToAgentSteps, subscribeToTaskEvents, subscribeToWorkerStatus } from '../services/eventStream';
import './AgentConsole.css';

function AgentConsole() {
  const [agentStatus, setAgentStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [currentTask, setCurrentTask] = useState(null);
  const [agentSteps, setAgentSteps] = useState([]);
  const [logs, setLogs] = useState([]);
  const logsEndRef = useRef(null);

  useEffect(() => {
    fetchAgentStatus();

    // 连接到 SSE 事件流
    eventStream.connect();

    // 订阅连接状态
    const unsubConnection = eventStream.subscribe('connection.status', (data) => {
      setConnectionStatus(data.status);
      addLog(`连接状态: ${data.status}`, 'system');
    });

    // 订阅 Agent 步骤事件
    const unsubAgentSteps = subscribeToAgentSteps((data, type) => {
      handleAgentStep(data, type);
    });

    // 订阅任务事件
    const unsubTaskEvents = subscribeToTaskEvents((data, type) => {
      handleTaskEvent(data, type);
    });

    // 订阅 Worker 状态
    const unsubWorkerStatus = subscribeToWorkerStatus((data) => {
      addLog(`Worker 状态: ${data.status} - ${data.message || ''}`, 'worker');
    });

    // 清理函数
    return () => {
      unsubConnection();
      unsubAgentSteps();
      unsubTaskEvents();
      unsubWorkerStatus();
      eventStream.disconnect();
    };
  }, []);

  // 自动滚动日志到底部
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  const addLog = (message, type = 'info') => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs(prev => [...prev, { timestamp, message, type }]);
  };

  const handleAgentStep = (data, type) => {
    const stepInfo = {
      id: `${data.task_id}-${data.step_index}-${Date.now()}`,
      taskId: data.task_id,
      chapterId: data.chapter_id,
      agent: data.agent,
      stepIndex: data.step_index,
      status: type === 'agent.step.started' ? 'running' :
               type === 'agent.step.completed' ? 'completed' : 'failed',
      tokens: data.tokens,
      cost: data.cost,
      error: data.error,
      rewriteRound: data.rewrite_round,
      timestamp: new Date(),
    };

    setAgentSteps(prev => {
      // 如果是开始事件，添加新步骤
      if (type === 'agent.step.started') {
        return [...prev, stepInfo];
      }
      // 如果是完成或失败事件，更新现有步骤
      return prev.map(step =>
        step.taskId === data.task_id &&
        step.agent === data.agent &&
        step.stepIndex === data.step_index &&
        step.status === 'running'
          ? { ...step, ...stepInfo }
          : step
      );
    });

    // 添加日志
    const agentEmoji = getAgentEmoji(data.agent);
    if (type === 'agent.step.started') {
      addLog(`${agentEmoji} ${data.agent} 步骤 ${data.step_index} 开始${data.rewrite_round ? ` (第${data.rewrite_round}轮重写)` : ''}`, 'step-start');
    } else if (type === 'agent.step.completed') {
      addLog(`${agentEmoji} ${data.agent} 步骤完成 | Tokens: ${data.tokens || 0} | 成本: $${(data.cost || 0).toFixed(4)}${data.new_score ? ` | 新评分: ${data.new_score}` : ''}`, 'step-complete');
    } else if (type === 'agent.step.failed') {
      addLog(`${agentEmoji} ${data.agent} 步骤失败: ${data.error}`, 'step-error');
    }
  };

  const handleTaskEvent = (data, type) => {
    if (type === 'task.started') {
      setCurrentTask({
        id: data.task_id,
        chapterId: data.chapter_id,
        chapterIndex: data.chapter_index,
        chapterTitle: data.chapter_title,
        status: 'running',
        startTime: new Date(),
      });
      addLog(`🚀 任务开始: ${data.chapter_title} (章节 #${data.chapter_index})`, 'task-start');
    } else if (type === 'task.completed') {
      setCurrentTask(prev => prev ? { ...prev, status: 'completed', ...data } : null);
      addLog(`✅ 任务完成: ${data.word_count} 字 | 评分: ${data.final_score}`, 'task-complete');
      // 刷新状态
      fetchAgentStatus();
    } else if (type === 'task.failed') {
      setCurrentTask(prev => prev ? { ...prev, status: 'failed', error: data.error } : null);
      addLog(`❌ 任务失败: ${data.error}`, 'task-error');
    }
  };

  const getAgentEmoji = (agent) => {
    const emojis = {
      'Planner': '📋',
      'Draft': '✍️',
      'Critic': '🔍',
      'Rewrite': '🔄',
      'Re-Critic': '🔎',
      'Continuity': '🔗',
      'Learning': '📚',
      'MemoryUpdate': '🧠',
    };
    return emojis[agent] || '🤖';
  };

  const fetchAgentStatus = async () => {
    try {
      const response = await api.get('/agents/status');
      setAgentStatus(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching agent status:', error);
      setLoading(false);
    }
  };

  const handleGenerateChapter = async () => {
    try {
      const response = await api.post('/agents/generate-chapter', {
        project_id: 1, chapter_index: 1, title: '测试章节'
      });
      addLog(`📤 提交生成请求: ${response.data.message || '成功'}`, 'system');
    } catch (error) {
      console.error('Error generating chapter:', error);
      addLog(`提交生成请求失败: ${error.message}`, 'error');
    }
  };

  const clearLogs = () => {
    setLogs([]);
  };

  const getConnectionStatusEmoji = () => {
    switch (connectionStatus) {
      case 'connected': return '🟢';
      case 'disconnected': return '⚪';
      case 'error':
      case 'failed': return '🔴';
      default: return '🟡';
    }
  };

  if (loading) {
    return <div className="loading">加载中...</div>;
  }

  return (
    <div className="agent-console">
      <header className="page-header">
        <h1>🤖 Agent 控制台</h1>
        <div className="header-actions">
          <span className="connection-status" title={`SSE 连接: ${connectionStatus}`}>
            {getConnectionStatusEmoji()} 实时推送
          </span>
          <button className="btn-primary" onClick={handleGenerateChapter}>
            📝 生成测试章节
          </button>
        </div>
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

          {currentTask && (
            <div className="current-task">
              <h4>当前任务</h4>
              <div className={`task-card ${currentTask.status}`}>
                <div className="task-title">{currentTask.chapterTitle}</div>
                <div className="task-meta">
                  章节 #{currentTask.chapterIndex} | 状态: {currentTask.status}
                </div>
                {currentTask.word_count && (
                  <div className="task-result">
                    📊 {currentTask.word_count} 字 | ⭐ {currentTask.final_score} 分
                  </div>
                )}
                {currentTask.error && (
                  <div className="task-error">❌ {currentTask.error}</div>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="agent-workspace">
          <h3>执行步骤</h3>
          {agentSteps.length === 0 ? (
            <p className="empty">暂无执行步骤</p>
          ) : (
            <div className="steps-list">
              {agentSteps.slice(-10).map((step) => (
                <div key={step.id} className={`step-item ${step.status}`}>
                  <div className="step-header">
                    <span className="step-agent">{getAgentEmoji(step.agent)} {step.agent}</span>
                    <span className={`step-status-badge ${step.status}`}>
                      {step.status === 'running' ? '⏳' :
                       step.status === 'completed' ? '✅' : '❌'}
                    </span>
                  </div>
                  <div className="step-details">
                    <span>步骤 {step.stepIndex}</span>
                    {step.rewriteRound && <span>重写 #{step.rewriteRound}</span>}
                    {step.tokens > 0 && <span>Tokens: {step.tokens}</span>}
                    {step.cost > 0 && <span>成本: ${step.cost.toFixed(4)}</span>}
                  </div>
                  {step.error && (
                    <div className="step-error-message">{step.error}</div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="agent-output">
          <div className="output-header">
            <h3>实时日志</h3>
            <button className="btn-clear" onClick={clearLogs}>清除</button>
          </div>
          <div className="logs-container">
            {logs.length === 0 ? (
              <p className="empty">等待事件...</p>
            ) : (
              <div className="logs-list">
                {logs.map((log, index) => (
                  <div key={index} className={`log-item ${log.type}`}>
                    <span className="log-time">{log.timestamp}</span>
                    <span className="log-message">{log.message}</span>
                  </div>
                ))}
                <div ref={logsEndRef} />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default AgentConsole;

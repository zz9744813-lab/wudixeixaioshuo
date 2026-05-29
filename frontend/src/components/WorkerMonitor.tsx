/**
 * WorkerMonitor - Worker 实时监控面板
 * 显示 Worker 状态、当前任务、Agent 进度
 */
import React from 'react';
import { useSSEContext } from '../hooks/SSEContext';
import './WorkerMonitor.css';

interface AgentStep {
  task_id: number;
  chapter_id: number;
  chapter_title?: string;
  agent: string;
  step_index: number;
  rewrite_round?: number;
  current_score?: number;
  tokens?: number;
  cost?: number;
  new_score?: number;
  error?: string;
}

interface TaskInfo {
  task_id: number;
  chapter_id: number;
  chapter_title: string;
  chapter_index?: number;
}

export function WorkerMonitor() {
  const { isConnected, lastEvent, events } = useSSEContext();

  // 解析当前任务
  const currentTask = React.useMemo(() => {
    const started = events
      .slice()
      .reverse()
      .find(e => e.type === 'task.started');
    return started?.data as TaskInfo | undefined;
  }, [events]);

  // 解析当前步骤
  const currentStep = React.useMemo(() => {
    const steps = events.filter(e =>
      e.type === 'agent.step.started' ||
      e.type === 'agent.step.completed' ||
      e.type === 'agent.step.failed'
    );

    // 找到最后一个 started 但没有 completed/failed 的步骤
    for (let i = steps.length - 1; i >= 0; i--) {
      const step = steps[i];
      if (step.type === 'agent.step.started') {
        // 检查是否有对应的完成事件
        const hasCompleted = steps.slice(i + 1).some(
          s =>
            (s.type === 'agent.step.completed' || s.type === 'agent.step.failed') &&
            s.data.task_id === step.data.task_id &&
            s.data.agent === step.data.agent &&
            s.data.step_index === step.data.step_index &&
            s.data.rewrite_round === step.data.rewrite_round
        );
        if (!hasCompleted) {
          return { ...step.data, status: 'running' } as AgentStep & { status: string };
        }
      }
    }

    // 返回最后一个完成的步骤
    const lastCompleted = steps
      .slice()
      .reverse()
      .find(e =>
        e.type === 'agent.step.completed' ||
        e.type === 'agent.step.failed'
      );

    if (lastCompleted) {
      return {
        ...lastCompleted.data,
        status: lastCompleted.type === 'agent.step.completed' ? 'completed' : 'failed',
      } as AgentStep & { status: string };
    }

    return null;
  }, [events]);

  // 解析任务状态
  const taskStatus = React.useMemo(() => {
    const lastTaskEvent = events
      .slice()
      .reverse()
      .find(e =>
        e.type === 'task.started' ||
        e.type === 'task.completed' ||
        e.type === 'task.failed'
      );

    if (!lastTaskEvent) return 'idle';

    switch (lastTaskEvent.type) {
      case 'task.started':
        return 'running';
      case 'task.completed':
        return 'completed';
      case 'task.failed':
        return 'failed';
      default:
        return 'idle';
    }
  }, [events]);

  // 解析 Worker 状态
  const workerStatus = React.useMemo(() => {
    const workerEvent = events
      .slice()
      .reverse()
      .find(e => e.type === 'worker.status');
    return workerEvent?.data?.status || 'unknown';
  }, [events]);

  // 计算统计数据
  const stats = React.useMemo(() => {
    const completed = events.filter(e => e.type === 'task.completed').length;
    const failed = events.filter(e => e.type === 'task.failed').length;
    const totalTokens = events
      .filter(e => e.type === 'agent.step.completed')
      .reduce((sum, e) => sum + (e.data.tokens || 0), 0);
    const totalCost = events
      .filter(e => e.type === 'agent.step.completed')
      .reduce((sum, e) => sum + (e.data.cost || 0), 0);

    return { completed, failed, totalTokens, totalCost };
  }, [events]);

  // Agent 步骤顺序
  const agentOrder = ['Planner', 'Draft', 'Critic', 'Rewrite', 'Re-Critic', 'Continuity', 'Learning', 'MemoryUpdate'];

  const getAgentStatus = (agentName: string) => {
    if (!currentStep) return 'pending';
    if (currentStep.agent === agentName) return currentStep.status;

    const agentIndex = agentOrder.indexOf(agentName);
    const currentIndex = agentOrder.indexOf(currentStep.agent);

    if (agentIndex < currentIndex) return 'completed';
    return 'pending';
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return '✓';
      case 'running':
        return '◌';
      case 'failed':
        return '✗';
      default:
        return '○';
    }
  };

  const getStatusClass = (status: string) => {
    switch (status) {
      case 'completed':
        return 'status-completed';
      case 'running':
        return 'status-running';
      case 'failed':
        return 'status-failed';
      default:
        return 'status-pending';
    }
  };

  return (
    <div className="worker-monitor">
      {/* 连接状态 */}
      <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
        <span className="status-dot" />
        {isConnected ? '已连接' : '已断开'}
      </div>

      {/* Worker 状态 */}
      <div className="worker-status">
        <h3>Worker 状态</h3>
        <div className={`status-badge ${workerStatus}`}>
          {workerStatus === 'running' && '运行中'}
          {workerStatus === 'paused' && '已暂停'}
          {workerStatus === 'stopped' && '已停止'}
          {workerStatus === 'unknown' && '未知'}
        </div>
      </div>

      {/* 当前任务 */}
      {currentTask && (
        <div className="current-task">
          <h3>当前任务</h3>
          <div className="task-info">
            <div className="task-title">
              {currentTask.chapter_title || `章节 #${currentTask.chapter_id}`}
            </div>
            <div className={`task-status ${taskStatus}`}>
              {taskStatus === 'running' && '写作中...'}
              {taskStatus === 'completed' && '已完成'}
              {taskStatus === 'failed' && '失败'}
            </div>
          </div>
        </div>
      )}

      {/* Agent 流水线 */}
      <div className="agent-pipeline">
        <h3>写作流水线</h3>
        <div className="pipeline-steps">
          {agentOrder.map((agent) => {
            const status = getAgentStatus(agent);
            return (
              <div key={agent} className={`pipeline-step ${getStatusClass(status)}`}>
                <span className="step-icon">{getStatusIcon(status)}</span>
                <span className="step-name">{agent}</span>
                {currentStep?.agent === agent && currentStep.rewrite_round && (
                  <span className="rewrite-round">#{currentStep.rewrite_round}</span>
                )}
                {currentStep?.agent === agent && currentStep.current_score !== undefined && (
                  <span className="current-score">{currentStep.current_score}分</span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* 实时统计 */}
      <div className="realtime-stats">
        <h3>实时统计</h3>
        <div className="stats-grid">
          <div className="stat-item">
            <span className="stat-value">{stats.completed}</span>
            <span className="stat-label">已完成</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">{stats.failed}</span>
            <span className="stat-label">失败</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">{(stats.totalTokens / 1000).toFixed(1)}k</span>
            <span className="stat-label">Tokens</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">${stats.totalCost.toFixed(4)}</span>
            <span className="stat-label">成本</span>
          </div>
        </div>
      </div>

      {/* 事件日志 */}
      <div className="event-log">
        <h3>事件日志</h3>
        <div className="log-container">
          {events.slice(-20).map((event, idx) => (
            <div key={idx} className={`log-entry ${event.type}`}>
              <span className="log-time">
                {new Date(event.timestamp).toLocaleTimeString()}
              </span>
              <span className="log-type">{event.type}</span>
              <span className="log-data">
                {event.data.agent && `${event.data.agent} `}
                {event.data.chapter_title || `章节#${event.data.chapter_id}`}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

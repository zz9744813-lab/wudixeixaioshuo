import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../services/api';
import './Tasks.css';

function Tasks() {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTasks();
  }, []);

  const fetchTasks = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/tasks/`);
      const data = await response.json();
      setTasks(data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching tasks:', error);
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      pending: '#888',
      running: '#3b82f6',
      paused: '#f59e0b',
      completed: '#10b981',
      failed: '#ef4444',
      cancelled: '#6b7280',
    };
    return colors[status] || '#888';
  };

  const getStatusLabel = (status) => {
    const labels = {
      pending: '待处理',
      running: '运行中',
      paused: '暂停',
      completed: '已完成',
      failed: '失败',
      cancelled: '已取消',
    };
    return labels[status] || status;
  };

  if (loading) {
    return <div className="loading">加载中...</div>;
  }

  return (
    <div className="tasks-page">
      <header className="page-header">
        <h1>📋 任务队列</h1>
      </header>

      <div className="tasks-list">
        {tasks.length === 0 ? (
          <div className="empty-state">
            <p>暂无任务</p>
          </div>
        ) : (
          tasks.map((task) => (
            <div key={task.id} className="task-item">
              <div className="task-info">
                <span className="task-type">{task.task_type}</span>
                <span
                  className="task-status"
                  style={{ background: getStatusColor(task.status) }}
                >
                  {getStatusLabel(task.status)}
                </span>
              </div>
              <div className="task-meta">
                <span>项目: {task.project_id}</span>
                <span>优先级: {task.priority}</span>
                <span>{new Date(task.created_at).toLocaleString()}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default Tasks;

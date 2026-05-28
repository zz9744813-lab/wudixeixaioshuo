import React, { useState } from 'react';
import { API_BASE_URL } from '../services/api';
import './WritingFactory.css';

function WritingFactory() {
  const [isRunning, setIsRunning] = useState(false);
  const [logs, setLogs] = useState([]);

  const handleStart = () => {
    setIsRunning(true);
    setLogs([...logs, { time: new Date().toLocaleTimeString(), message: '启动 24小时写作循环...' }]);
  };

  const handleStop = () => {
    setIsRunning(false);
    setLogs([...logs, { time: new Date().toLocaleTimeString(), message: '已暂停写作循环' }]);
  };

  return (
    <div className="writing-factory">
      <header className="page-header">
        <h1>🏭 24小时写作工厂</h1>
        <div className="factory-controls">
          {isRunning ? (
            <button className="btn-danger" onClick={handleStop}>
              ⏸️ 暂停
            </button>
          ) : (
            <button className="btn-primary" onClick={handleStart}>
              ▶️ 启动
            </button>
          )}
        </div>
      </header>

      <div className="factory-status">
        <div className={`status-indicator ${isRunning ? 'running' : 'stopped'}`}>
          <span className="dot"></span>
          <span>{isRunning ? '运行中' : '已停止'}</span>
        </div>
      </div>

      <div className="factory-content">
        <div className="factory-section">
          <h3>实时日志</h3>
          <div className="log-container">
            {logs.length === 0 ? (
              <p className="empty">暂无日志</p>
            ) : (
              logs.map((log, idx) => (
                <div key={idx} className="log-line">
                  <span className="log-time">{log.time}</span>
                  <span className="log-message">{log.message}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default WritingFactory;

import React from 'react';
import styles from './AgentLogPanel.module.css';

const LEVEL_STYLE = {
  info: 'info',
  success: 'success',
  warning: 'warning',
  error: 'error',
};

export default function AgentLogPanel({ logs = [], emptyText = '暂无日志' }) {
  if (!logs.length) {
    return <div className={styles.empty}>{emptyText}</div>;
  }

  return (
    <div className={styles.root}>
      <div className={styles.header}>
        <span className={styles.title}>执行日志</span>
        <span className={styles.count}>{logs.length}</span>
      </div>
      <div className={styles.list}>
        {logs.map((log, idx) => (
          <div key={idx} className={`${styles.row} ${styles[LEVEL_STYLE[log.level] || 'info']}`}>
            {log.time && <span className={styles.time}>{log.time}</span>}
            <span className={styles.message}>{log.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

AgentLogPanel.defaultProps = {
  logs: [],
  emptyText: '暂无日志',
};

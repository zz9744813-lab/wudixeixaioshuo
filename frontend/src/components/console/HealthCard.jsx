import React from 'react';
import StatusPill from './StatusPill';
import styles from './HealthCard.module.css';

export default function HealthCard({
  title,
  status = 'unknown',
  description,
  meta,
  actions,
}) {
  return (
    <div className={`${styles.root} ${styles[status] || ''}`}>
      <div className={styles.header}>
        <span className={styles.title}>{title}</span>
        <StatusPill status={status === 'ok' ? 'success' : status === 'error' ? 'danger' : 'warning'} label={statusLabel(status)} />
      </div>
      {description && <p className={styles.desc}>{description}</p>}
      {meta && <div className={styles.meta}>{meta}</div>}
      {actions && <div className={styles.actions}>{actions}</div>}
    </div>
  );
}

function statusLabel(status) {
  switch (status) {
    case 'ok':
      return '正常';
    case 'error':
      return '异常';
    case 'warning':
      return '警告';
    default:
      return '未知';
  }
}

import React from 'react';
import styles from './EmptyPanel.module.css';

export default function EmptyPanel({
  title = '暂无数据',
  description,
  action,
}) {
  return (
    <div className={styles.root}>
      <div className={styles.icon}>
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <path d="M9 9h6M9 13h6M9 17h4" />
        </svg>
      </div>
      <p className={styles.title}>{title}</p>
      {description && <p className={styles.desc}>{description}</p>}
      {action && <div className={styles.action}>{action}</div>}
    </div>
  );
}

EmptyPanel.defaultProps = {
  description: undefined,
  action: undefined,
};

import React from 'react';
import styles from './StatusPill.module.css';

export default function StatusPill({ status, label, dot = true }) {
  return (
    <span className={`${styles.root} ${styles[status] || ''}`}>
      {dot && <span className={styles.dot} />}
      <span className={styles.label}>{label}</span>
    </span>
  );
}

StatusPill.defaultProps = {
  dot: true,
};

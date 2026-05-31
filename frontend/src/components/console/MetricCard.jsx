import React from 'react';
import styles from './MetricCard.module.css';

export default function MetricCard({
  label,
  value,
  unit,
  hint,
  trend,
  status = 'muted',
}) {
  return (
    <div className={styles.root}>
      <div className={styles.header}>
        <span className={styles.label}>{label}</span>
        {trend && <span className={`${styles.trend} ${styles[status]}`}>{trend}</span>}
      </div>
      <div className={`${styles.valueWrap} ${status !== 'muted' ? styles[status] : ''}`}>
        <span className={styles.value}>{typeof value === 'number' ? value.toLocaleString() : value}</span>
        {unit && <span className={styles.unit}>{unit}</span>}
      </div>
      {hint && <div className={styles.hint}>{hint}</div>}
    </div>
  );
}

MetricCard.defaultProps = {
  unit: undefined,
  hint: undefined,
  trend: undefined,
  status: 'muted',
};

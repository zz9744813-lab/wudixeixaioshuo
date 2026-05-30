import React from 'react';
import styles from './StatCard.module.css';

export function StatCard({ label, value, unit, hint }) {
  return (
    <div className={styles.card}>
      <div className={styles.label}>{label}</div>
      <div className={styles.value}>
        {value}
        {unit && <span className={styles.unit}>{unit}</span>}
      </div>
      {hint && <div className={styles.hint}>{hint}</div>}
    </div>
  );
}

export default StatCard;

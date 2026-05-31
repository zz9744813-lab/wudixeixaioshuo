import React from 'react';
import styles from './PageHeader.module.css';

export default function PageHeader({
  title,
  subtitle,
  icon,
  status,
  actions,
}) {
  return (
    <div className={styles.root}>
      <div className={styles.left}>
        {icon && <span className={styles.icon}>{icon}</span>}
        <div className={styles.texts}>
          <h1 className={styles.title}>{title}</h1>
          {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
        </div>
      </div>
      {(status || actions) && (
        <div className={styles.right}>
          {status && <span className={styles.status}>{status}</span>}
          {actions && <div className={styles.actions}>{actions}</div>}
        </div>
      )}
    </div>
  );
}

PageHeader.defaultProps = {
  subtitle: undefined,
  icon: undefined,
  status: undefined,
  actions: undefined,
};

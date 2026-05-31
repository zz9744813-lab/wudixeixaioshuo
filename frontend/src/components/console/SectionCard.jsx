import React from 'react';
import styles from './SectionCard.module.css';

export default function SectionCard({
  title,
  subtitle,
  actions,
  children,
}) {
  return (
    <div className={styles.root}>
      {(title || subtitle || actions) && (
        <div className={styles.header}>
          <div className={styles.texts}>
            {title && <h3 className={styles.title}>{title}</h3>}
            {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
          </div>
          {actions && <div className={styles.actions}>{actions}</div>}
        </div>
      )}
      <div className={styles.body}>{children}</div>
    </div>
  );
}

SectionCard.defaultProps = {
  subtitle: undefined,
  actions: undefined,
};

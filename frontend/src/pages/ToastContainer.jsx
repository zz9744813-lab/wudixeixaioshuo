import React from 'react';
import { useToast } from '../contexts/ToastContext';
import { Icon } from '../components/ui/Icon';
import styles from './ToastContainer.module.css';

export default function ToastContainer() {
  const { toasts, removeToast } = useToast();

  if (toasts.length === 0) return null;

  const iconByType = {
    success: 'CheckCircle2',
    error: 'XCircle',
    warning: 'AlertTriangle',
    info: 'Info',
  };
  const clsByType = {
    success: styles.success,
    error: styles.error,
    warning: styles.warning,
    info: styles.info,
  };

  return (
    <div className={styles.root} aria-live="polite">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`${styles.item} ${clsByType[t.type] || styles.info}`}
          role="status"
        >
          <Icon name={iconByType[t.type] || 'Info'} size={16} className={styles.icon} />
          <span className={styles.message}>{t.message}</span>
          <button
            type="button"
            className={styles.close}
            onClick={() => removeToast(t.id)}
            aria-label="关闭"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}

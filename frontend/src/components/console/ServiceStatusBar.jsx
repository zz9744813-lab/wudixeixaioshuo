import React from 'react';
import StatusPill from './StatusPill';
import styles from './ServiceStatusBar.module.css';

export default function ServiceStatusBar({
  backend,
  worker,
  model,
  database,
  costText,
}) {
  const items = [
    { key: 'backend', label: 'Backend', status: backend },
    { key: 'worker', label: 'Worker', status: worker },
    { key: 'model', label: 'Model', status: model },
    { key: 'database', label: 'Database', status: database },
  ].filter((item) => item.status !== undefined);

  if (!items.length && !costText) return null;

  return (
    <div className={styles.root}>
      <div className={styles.items}>
        {items.map((item) => (
          <StatusPill
            key={item.key}
            status={mapStatus(item.status)}
            label={`${item.label} ${item.labelText || ''}`}
          />
        ))}
        {costText && <span className={styles.cost}>{costText}</span>}
      </div>
    </div>
  );
}

function mapStatus(status) {
  switch (status) {
    case 'ok':
    case 'configured':
    case 'running':
      return 'success';
    case 'missing':
    case 'idle':
      return 'warning';
    case 'error':
      return 'danger';
    default:
      return 'muted';
  }
}

ServiceStatusBar.defaultProps = {
  backend: undefined,
  worker: undefined,
  model: undefined,
  database: undefined,
  costText: undefined,
};

import React from 'react';
import styles from './PipelineSteps.module.css';

const STATUS_LABEL = {
  done: '完成',
  running: '执行中',
  pending: '等待',
  failed: '失败',
};

const STATUS_ICON = {
  done: '✓',
  running: '⌛',
  pending: '○',
  failed: '✕',
};

export default function PipelineSteps({ steps = [] }) {
  if (!steps.length) {
    return <div className={styles.empty}>暂无执行步骤</div>;
  }

  return (
    <div className={styles.root}>
      {steps.map((step, idx) => (
        <div key={step.key || idx} className={`${styles.step} ${styles[step.status] || ''}`}>
          <div className={styles.lineWrap}>
            <div className={styles.iconWrap}>
              <span className={styles.icon}>{STATUS_ICON[step.status] || '○'}</span>
            </div>
            {idx < steps.length - 1 && <div className={styles.line} />}
          </div>
          <div className={styles.content}>
            <div className={styles.topRow}>
              <span className={styles.label}>{step.label || step.key}</span>
              <span className={`${styles.status} ${styles[step.status] || ''}`}>
                {STATUS_LABEL[step.status] || step.status}
              </span>
            </div>
            {(step.duration || step.tokens) && (
              <div className={styles.meta}>
                {step.duration && <span>耗时 {step.duration}</span>}
                {step.tokens && <span> Tokens {step.tokens.toLocaleString()}</span>}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

PipelineSteps.defaultProps = {
  steps: [],
};

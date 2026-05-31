import React from 'react';
import { Icon } from '../components/ui/Icon';
import { useEventSource } from '../hooks/useEventSource';
import { useToast } from '../contexts/ToastContext';
import styles from './ProgressIndicator.module.css';

export default function ProgressIndicator({ taskId }) {
  const apiKey = typeof window !== 'undefined' ? (localStorage.getItem('APP_API_KEY') || '') : '';
  const baseUrl =
    typeof process !== 'undefined'
      ? process.env.REACT_APP_API_URL
        ? `${process.env.REACT_APP_API_URL}/events/stream`
        : 'http://localhost:8000/api/events/stream'
      : 'http://localhost:8000/api/events/stream';

  const { events, connected } = useEventSource(baseUrl, { token: apiKey || undefined, auto: Boolean(apiKey) });
  const { info } = useToast();

  const latestStep = events
    .filter((e) => e.event?.startsWith('agent.step.'))
    .slice(-1)[0];

  const stepLabel = latestStep
    ? {
        step_index: latestStep.data?.step_index,
        agent_name: latestStep.data?.agent,
        rewrite_round: latestStep.data?.rewrite_round,
      }
    : null;

  React.useEffect(() => {
    if (!latestStep) return;
    const round = stepLabel?.rewrite_round;
    const name = stepLabel?.agent_name || '';
    const label = round ? `${name} #${round}` : `${name}`;
    info(`当前阶段：${label}`, 2500);
  }, [latestStep]);

  if (!connected && !latestStep) return null;

  const statusText = connected ? 'SSE 已连接' : 'SSE 未连接';
  const round = stepLabel?.rewrite_round ? ` ·轮次 ${stepLabel.rewrite_round}` : '';

  return (
    <div className={styles.root}>
      <span className={`${styles.dot} ${connected ? styles.on : styles.off}`} />
      <span className={styles.text}>
        {statusText}
        {stepLabel ? ` · 当前：${stepLabel.agent_name}${round}` : ''}
      </span>
    </div>
  );
}

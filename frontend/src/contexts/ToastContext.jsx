import { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react';
import { useEventSource } from '../hooks/useEventSource';

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const idRef = useRef(0);
  const seenEvents = useRef(new Set());
  const getApiKey = useCallback(() => process.env.REACT_APP_API_KEY || localStorage.getItem('APP_API_KEY') || '', []);

  const addToast = useCallback((message, type = 'info', duration = 4000) => {
    const id = ++idRef.current;
    setToasts((prev) => [...prev, { id, message, type }]);
    if (duration > 0) {
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, duration);
    }
    return id;
  }, []);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const success = useCallback((msg, dur) => addToast(msg, 'success', dur), [addToast]);
  const error = useCallback((msg, dur) => addToast(msg, 'error', dur || 6000), [addToast]);
  const warning = useCallback((msg, dur) => addToast(msg, 'warning', dur), [addToast]);
  const info = useCallback((msg, dur) => addToast(msg, 'info', dur), [addToast]);

  // Auto-toast from SSE events (reader training + pipeline)
  const sseBase = process.env.REACT_APP_API_URL
    ? `${process.env.REACT_APP_API_URL}/events/stream`
    : 'http://localhost:8000/api/events/stream';
  const token = getApiKey();
  const { connected } = useEventSource(sseBase, { token, auto: Boolean(token) });

  useEffect(() => {
    if (!token) return;
    const handler = (ev) => {
      const d = ev.detail || {};
      if (!d || typeof d !== 'object') return;
      const key = `${d.event}:${d.data?.batch_id || d.data?.feedback_id || d.data?.task_id || ''}`;
      if (seenEvents.current.has(key)) return;
      seenEvents.current.add(key);
      // prune seen set occasionally
      if (seenEvents.current.size > 600) seenEvents.current = new Set([key]);
      const { event, data } = d;
      if (event === 'feedback.queued') {
        info(data?.message || '反馈已入队', 3500);
      } else if (event === 'feedback.batch.processed') {
        success('真人反馈批次已处理并生成规则', 4500);
      } else if (event === 'feedback.batch.failed') {
        error(`批处理失败：${data?.error || '未知错误'}`, 6000);
      } else if (event === 'critic.calibration.requested') {
        warning('检测到真人评分与系统偏差，已触发 Critic 校准', 6000);
      } else if (event === 'critic.calibrated') {
        success('Critic 校准完成', 4000);
      } else if (event === 'evolution.reader_triggered') {
        info('已按真人反馈触发 Prompt 进化', 4500);
      } else if (event?.startsWith('agent.step.')) {
        // 进度事件可由 TaskDetail 自行消费，此处做轻量提示
      }
    };
    window.addEventListener('app:api-error', handler);
    return () => window.removeEventListener('app:api-error', handler);
  }, [token, error, info, success, warning]);

  return (
    <ToastContext.Provider value={{ toasts, removeToast, success, error, warning, info }}>
      {children}
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}

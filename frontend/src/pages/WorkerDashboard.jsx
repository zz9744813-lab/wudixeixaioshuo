import React, { useCallback, useEffect, useState } from 'react';
import api from '../services/api';
import { getApiErrorMessage } from '../services/api';
import { useToast } from '../contexts/ToastContext';
import { useConfirm } from '../hooks/useConfirm';
import { Icon } from '../components/ui/Icon';
import { AsyncState } from '../components/ui/AsyncState';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { StatCard } from '../components/ui/StatCard';
import ConfirmModal from '../components/ConfirmModal';
import { toObject } from '../utils/nullSafety';
import styles from './WorkerDashboard.module.css';

const PAGE_TITLE = '24小时自动写作控制台';
const PAGE_ICON = 'Bot';

const WORKER_STATUS_MAP = {
  idle: { label: '空闲', variant: 'muted' },
  running: { label: '运行中', variant: 'success' },
  paused: { label: '已暂停', variant: 'warning' },
  stopped: { label: '已停止', variant: 'danger' },
};

export default function WorkerDashboard() {
  const toast = useToast();
  const { confirm, state: confirmState, handleOk, handleCancel } = useConfirm();

  const [status, setStatus] = useState(null);
  const [stats, setStats] = useState(null);
  const [health, setHealth] = useState(null);
  const [statusError, setStatusError] = useState('');
  const [statsError, setStatsError] = useState('');
  const [healthError, setHealthError] = useState('');
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [loadingStats, setLoadingStats] = useState(true);
  const [loadingHealth, setLoadingHealth] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  // P0-5: 三个接口独立加载，不因一个失败整页崩溃
  const fetchStatus = useCallback(async () => {
    setStatusError('');
    try {
      const res = await api.get('/worker/status');
      setStatus(res.data);
    } catch (err) {
      setStatusError(getApiErrorMessage(err));
    } finally {
      setLoadingStatus(false);
    }
  }, []);

  const fetchStats = useCallback(async () => {
    setStatsError('');
    try {
      const res = await api.get('/worker/stats');
      setStats(toObject(res.data));
    } catch (err) {
      setStatsError(getApiErrorMessage(err));
    } finally {
      setLoadingStats(false);
    }
  }, []);

  const fetchHealth = useCallback(async () => {
    setHealthError('');
    try {
      const res = await api.get('/worker/health');
      setHealth(res.data);
    } catch (err) {
      setHealthError(getApiErrorMessage(err));
    } finally {
      setLoadingHealth(false);
    }
  }, []);

  const fetchAll = useCallback(async () => {
    setLoadingStatus(true);
    setLoadingStats(true);
    setLoadingHealth(true);
    await Promise.all([fetchStatus(), fetchStats(), fetchHealth()]);
  }, [fetchStatus, fetchStats, fetchHealth]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const sendControl = async (action) => {
    setActionLoading(true);
    try {
      const res = await api.post('/worker/control', { action });
      toast.success(res.data?.message || `Worker ${action} 成功`);
      fetchAll();
    } catch (err) {
      toast.error(getApiErrorMessage(err), 6000);
    } finally {
      setActionLoading(false);
    }
  };

  const handleResetStats = async () => {
    const ok = await confirm({ title: '重置统计', message: '确定要重置今日的 Worker 统计数据吗？' });
    if (!ok) return;
    try {
      await api.post('/worker/reset-stats');
      toast.success('统计已重置');
      fetchAll();
    } catch (err) { toast.error(getApiErrorMessage(err), 5000); }
  };

  const handleClearFailed = async () => {
    const ok = await confirm({ title: '清空失败任务', message: '确定要将所有失败的章节重置为待处理状态吗？' });
    if (!ok) return;
    try {
      const res = await api.post('/worker/queue/clear-failed');
      toast.success(res.data?.message || '已清空失败任务');
      fetchAll();
    } catch (err) { toast.error(getApiErrorMessage(err), 5000); }
  };

  const workerSt = status?.status || 'idle';
  const stInfo = WORKER_STATUS_MAP[workerSt] || WORKER_STATUS_MAP.idle;
  const statsObj = toObject(stats);
  const dailyStats = statsObj?.worker?.daily_stats || {};
  const queueData = statsObj?.queue || {};
  const queueItems = Array.isArray(queueData?.tasks) ? queueData.tasks : [];
  const progress = queueData?.progress || {};
  const healthObj = toObject(health);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}><Icon name={PAGE_ICON} size={22} /><span>{PAGE_TITLE}</span></h1>
        <Badge variant={stInfo.variant}>{stInfo.label}</Badge>
      </header>

      {/* 服务诊断栏 */}
      <div className={styles.healthBar}>
        <span className={styles.healthItem}>
          后端状态: {loadingStatus ? '检测中…' : statusError ? <span style={{color:'var(--color-danger)'}}>{statusError}</span> : <span style={{color:'var(--color-success)'}}>在线</span>}
        </span>
        <span className={styles.healthItem}>
          Worker: {loadingStats ? '检测中…' : statsError ? <span style={{color:'var(--color-danger)'}}>统计异常</span> : <span style={{color:'var(--color-success)'}}>正常</span>}
        </span>
        <span className={styles.healthItem}>
          数据库: {loadingHealth ? '检测中…' : healthError ? <span style={{color:'var(--color-danger)'}}>{healthError}</span> : !healthObj?.db_ok ? <span style={{color:'var(--color-danger)'}}>异常</span> : <span style={{color:'var(--color-success)'}}>正常</span>}
        </span>
        {healthObj?.warnings?.length > 0 && (
          <span className={styles.healthWarn}>警告: {healthObj.warnings.join('; ')}</span>
        )}
      </div>

      {/* Stats */}
      <AsyncState loading={loadingStatus} error={statusError} onRetry={fetchStatus} hideError={!!statsError}>
        <div className={styles.statsGrid}>
          <StatCard label="今日已写" value={(dailyStats.words_written || 0).toLocaleString()} unit="字" />
          <StatCard label="今日完成" value={dailyStats.tasks_completed || 0} unit="个" />
          <StatCard label="今日失败" value={dailyStats.tasks_failed || 0} unit="个" />
          <StatCard label="队列进度" value={`${progress.percentage || 0}%`} />
        </div>
      </AsyncState>

      {/* Controls */}
      <section className={styles.card}>
        <h2 className={styles.cardTitle}>Worker 控制</h2>
        <div className={styles.controlRow}>
          <Button variant="primary" onClick={() => sendControl('start')} disabled={actionLoading || workerSt === 'running'}>
            {actionLoading ? '操作中…' : '▶ 启动'}
          </Button>
          <Button variant="secondary" onClick={() => sendControl('pause')} disabled={actionLoading || workerSt !== 'running'}>
            ⏸ 暂停
          </Button>
          <Button variant="secondary" onClick={() => sendControl('resume')} disabled={actionLoading || workerSt !== 'paused'}>
            ▶ 恢复
          </Button>
          <Button variant="danger" onClick={() => sendControl('stop')} disabled={actionLoading || ['idle', 'stopped'].includes(workerSt)}>
            ⏹ 停止
          </Button>
          <div className={styles.spacer} />
          <Button variant="ghost" size="sm" onClick={handleResetStats}>重置统计</Button>
          <Button variant="ghost" size="sm" onClick={handleClearFailed}>清空失败任务</Button>
        </div>
        {status?.current_task && (
          <p className={styles.currentTask}>当前任务：{typeof status.current_task === 'string' ? status.current_task : JSON.stringify(status.current_task)}</p>
        )}
      </section>

      {/* Queue */}
      {statsError ? (
        <section className={styles.card}>
          <h2 className={styles.cardTitle}>📋 写作队列</h2>
          <div className={styles.errorBox}>
            <strong>队列统计加载失败</strong>
            <p>接口: <code>GET /api/worker/stats</code></p>
            <p>错误: {statsError}</p>
            <Button variant="secondary" size="sm" onClick={fetchStats}>重试</Button>
          </div>
        </section>
      ) : (
        <section className={styles.card}>
          <h2 className={styles.cardTitle}>📋 写作队列 ({queueItems.length})</h2>
          <AsyncState loading={false} error={null} isEmpty={queueItems.length === 0} emptyTitle="队列为空" hideLoading hideError>
            <div className={styles.queueList}>
              {queueItems.map((item, idx) => (
                <div key={item.id || item.chapter_id || idx} className={styles.queueItem}>
                  <span className={styles.queueIdx}>#{idx + 1}</span>
                  <span className={styles.queueName}>{item.project_name || `项目 ${item.project_id}`}</span>
                  <span className={styles.queueChapter}>第 {item.chapter_index || item.chapter_id} 章</span>
                  <Badge variant={item.status === 'completed' ? 'success' : item.status === 'failed' ? 'danger' : item.status === 'running' ? 'warning' : 'accent'}>
                    {item.status || 'pending'}
                  </Badge>
                  {item.error && <span className={styles.queueError}>{item.error}</span>}
                </div>
              ))}
            </div>
          </AsyncState>
        </section>
      )}

      <ConfirmModal state={confirmState} onOk={handleOk} onCancel={handleCancel} />
    </div>
  );
}

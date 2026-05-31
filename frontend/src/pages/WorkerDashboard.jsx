import React, { useCallback, useEffect, useState } from 'react';
import api from '../services/api';
import { getApiErrorMessage } from '../services/api';
import { useToast } from '../contexts/ToastContext';
import { useConfirm } from '../hooks/useConfirm';
import { AsyncState } from '../components/ui/AsyncState';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import ConfirmModal from '../components/ConfirmModal';
import { toObject } from '../utils/nullSafety';

import PageHeader from '../components/console/PageHeader';
import StatusPill from '../components/console/StatusPill';
import MetricCard from '../components/console/MetricCard';
import HealthCard from '../components/console/HealthCard';
import SectionCard from '../components/console/SectionCard';
import ServiceStatusBar from '../components/console/ServiceStatusBar';
import EmptyPanel from '../components/console/EmptyPanel';
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

  const backendOk = !statusError && healthObj?.db_ok !== false;
  const workerOk = workerSt === 'running' || workerSt === 'idle';
  const databaseOk = healthObj?.db_ok === true || healthObj?.database === 'connected';

  return (
    <div className={styles.page}>
      <PageHeader
        title={PAGE_TITLE}
        icon={<span style={{ fontSize: 18 }}>⚙️</span>}
        status={<StatusPill status={workerOk ? 'success' : 'warning'} label={stInfo.label} />}
      />

      <ServiceStatusBar
        backend={backendOk ? 'ok' : 'error'}
        worker={workerSt}
        database={databaseOk ? 'ok' : 'error'}
        costText={`今日预算 $${(dailyStats?.cost || 0).toFixed(4)}`}
      />

      <div className={styles.metricsGrid}>
        <MetricCard label="今日已写" value={(dailyStats.words_written || 0).toLocaleString()} unit="字" status="success" />
        <MetricCard label="今日完成" value={dailyStats.tasks_completed || 0} unit="个" status="success" />
        <MetricCard label="今日失败" value={dailyStats.tasks_failed || 0} unit="个" status={dailyStats.tasks_failed ? 'danger' : 'muted'} />
        <MetricCard label="队列进度" value={`${progress.percentage || 0}%`} unit="" status={progress.percentage >= 80 ? 'success' : 'info'} />
      </div>

      <SectionCard title="Worker 控制" subtitle="启动 / 暂停 / 恢复 / 停止">
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
      </SectionCard>

      <div className={styles.bottomGrid}>
        <SectionCard title="模型与服务状态">
          <div className={styles.healthGrid}>
            <HealthCard title="Backend" status={backendOk ? 'ok' : 'error'} description={backendOk ? 'API 正常运行' : '后端服务异常'} />
            <HealthCard title="Worker" status={workerOk ? 'ok' : 'error'} description={stInfo.label} meta={`挂起任务 ${statsObj?.queue?.pending || 0}`} />
            <HealthCard title="Database" status={databaseOk ? 'ok' : 'error'} description={databaseOk ? '连接正常' : '数据库异常'} meta={healthObj?.database_url_masked || healthObj?.database || ''} />
          </div>
          {(healthError || statusError) && (
            <div className={styles.errorBox}>
              <strong>诊断失败</strong>
              {statusError && <p>Status: {statusError}</p>}
              {healthError && <p>Health: {healthError}</p>}
            </div>
          )}
        </SectionCard>

        <SectionCard title="写作队列" subtitle={`${queueItems.length} 个任务`}>
          {queueItems.length === 0 ? (
            <EmptyPanel title="队列为空" description="当前没有待执行或进行中的任务" />
          ) : (
            <div className={styles.queueList}>
              {queueItems.map((item, idx) => (
                <div key={item.id || item.chapter_id || idx} className={styles.queueItem}>
                  <div className={styles.queueHeader}>
                    <span className={styles.queueTitle}>#{idx + 1} {item.project_name || `项目 ${item.project_id}`}</span>
                    <Badge variant={item.status === 'completed' ? 'success' : item.status === 'failed' ? 'danger' : item.status === 'running' ? 'warning' : 'accent'}>
                      {item.status || 'pending'}
                    </Badge>
                  </div>
                  <span className={styles.queueChapter}>第 {item.chapter_index || item.chapter_id} 章</span>
                  {item.error && <span className={styles.queueError}>{item.error}</span>}
                  {item.progress != null && (
                    <div className={styles.progressWrap}>
                      <div className={styles.progressBar} style={{ width: `${Math.min(100, item.progress)}%` }} />
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      </div>

      <ConfirmModal state={confirmState} onOk={handleOk} onCancel={handleCancel} />
    </div>
  );
}

import React, { useCallback, useEffect, useState } from 'react';
import api from '../services/api';
import { useToast } from '../contexts/ToastContext';
import PageHeader from '../components/console/PageHeader';
import StatusPill from '../components/console/StatusPill';
import MetricCard from '../components/console/MetricCard';
import HealthCard from '../components/console/HealthCard';
import SectionCard from '../components/console/SectionCard';
import PipelineSteps from '../components/console/PipelineSteps';
import AgentLogPanel from '../components/console/AgentLogPanel';
import ServiceStatusBar from '../components/console/ServiceStatusBar';
import EmptyPanel from '../components/console/EmptyPanel';
import styles from './DashboardV2.module.css';

const PAGE_TITLE = 'NovelForge 控制台';
const PAGE_SUBTITLE = '24小时小说 Agent 工作台 / 自动小说工厂';

const PIPELINE_STEPS = [
  { key: 'planner', label: 'Planner', status: 'pending' },
  { key: 'draft', label: 'Draft', status: 'pending' },
  { key: 'critic', label: 'Critic', status: 'pending' },
  { key: 'rewrite', label: 'Rewrite', status: 'pending' },
  { key: 'continuity', label: 'Continuity', status: 'pending' },
  { key: 'memory', label: 'MemoryUpdate', status: 'pending' },
];

export default function DashboardV2() {
  const toast = useToast();
  const [worker, setWorker] = useState({ status: 'unknown', stats: null, health: null });
  const [providers, setProviders] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    const results = await Promise.allSettled([
      api.get('/worker/status'),
      api.get('/worker/stats'),
      api.get('/worker/health'),
      api.get('/models/providers'),
      api.get('/models/roles'),
    ]);

    const [statusRes, statsRes, healthRes, providersRes, rolesRes] = results;

    if (statusRes.status === 'fulfilled') setWorker((w) => ({ ...w, status: statusRes.value.data?.status || 'unknown' }));
    if (statsRes.status === 'fulfilled') setWorker((w) => ({ ...w, stats: statsRes.value.data }));
    if (healthRes.status === 'fulfilled') setWorker((w) => ({ ...w, health: healthRes.value.data }));

    if (providersRes.status === 'fulfilled') setProviders(toArray(providersRes.value?.data));
    if (rolesRes.status === 'fulfilled') setRoles(toArray(rolesRes.value?.data));

    setLoading(false);
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const stats = worker.stats || {};
  const health = worker.health || {};
  const backendOk = health.db_ok !== false;
  const workerOk = worker.status === 'running' || worker.status === 'idle';
  const modelOk = providers.length > 0;
  const databaseOk = health.db_ok === true || health.database === 'connected';

  const workerStatusText = worker.status === 'running' ? '运行中' : worker.status === 'idle' ? '空闲' : worker.status === 'paused' ? '已暂停' : '未知';
  const modelStatusText = modelOk ? `已配置 (${providers.length})` : '未配置';

  return (
    <div className={styles.page}>
      <PageHeader
        title={PAGE_TITLE}
        subtitle={PAGE_SUBTITLE}
        status={<StatusPill status={workerOk ? 'success' : 'warning'} label={workerOk ? '安全基线运行中' : '服务待检'} />}
      />

      <ServiceStatusBar
        backend={backendOk ? 'ok' : 'error'}
        worker={worker.status}
        model={modelOk ? 'configured' : 'missing'}
        database={databaseOk ? 'ok' : 'error'}
        costText={`今日预算 $${(stats.today_cost || 0).toFixed(4)}`}
      />

      <div className={styles.metricsGrid}>
        <MetricCard
          label="今日已写"
          value={stats.today_words || 0}
          unit="字"
          trend={stats.today_words_ratio ? `+${stats.today_words_ratio}%` : undefined}
          status="success"
        />
        <MetricCard
          label="队列进度"
          value={stats.queue_progress != null ? Math.round(stats.queue_progress) : 0}
          unit="%"
          status={stats.queue_progress >= 80 ? 'success' : 'info'}
        />
        <MetricCard
          label="Model Provider"
          value={providers.length}
          unit="个"
          status={modelOk ? 'success' : 'warning'}
        />
        <MetricCard
          label="今日成本"
          value={(stats.today_cost || 0).toFixed(4)}
          unit="$"
          hint={`调用 ${stats.today_calls || 0} 次`}
          status={stats.today_cost > 5 ? 'warning' : 'muted'}
        />
      </div>

      <div className={styles.mainGrid}>
        <SectionCard title="Agent 流水线" subtitle="实时展示每一步执行状态">
          <PipelineSteps steps={PIPELINE_STEPS} />
          <AgentLogPanel logs={[]} emptyText="等待 Agent 启动..." />
        </SectionCard>

        <div className={styles.sideStack}>
          <SectionCard title="模型与服务状态">
            <div className={styles.healthGrid}>
              <HealthCard
                title="Backend"
                status={backendOk ? 'ok' : 'error'}
                description={backendOk ? 'API 正常运行' : '后端服务异常'}
                meta={health.database_url_masked || health.database || ''}
              />
              <HealthCard
                title="Worker"
                status={workerOk ? 'ok' : 'error'}
                description={workerStatusText}
                meta={`挂起任务 ${stats.pending_tasks || 0}`}
              />
              <HealthCard
                title="Model"
                status={modelOk ? 'ok' : 'error'}
                description={modelStatusText}
                meta={`Provider 数量: ${providers.length}`}
              />
              <HealthCard
                title="Database"
                status={databaseOk ? 'ok' : 'error'}
                description={databaseOk ? '连接正常' : '数据库异常'}
              />
            </div>
          </SectionCard>

          <SectionCard title="写作队列概览">
            {stats.queue && stats.queue.length ? (
              <div className={styles.list}>
                {stats.queue.map((task, idx) => (
                  <div key={idx} className={styles.queueItem}>
                    <div className={styles.queueHeader}>
                      <span className={styles.queueTitle}>{task.chapter_title || `章节 ${idx + 1}`}</span>
                      <StatusPill status={task.status === 'done' ? 'success' : task.status === 'running' ? 'info' : 'warning'} label={task.status || '等待'} />
                    </div>
                    {task.progress != null && (
                      <div className={styles.progressWrap}>
                        <div className={styles.progressBar} style={{ width: `${Math.min(100, task.progress)}%` }} />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <EmptyPanel title="队列为空" description="当前没有待执行或进行中的任务" />
            )}
          </SectionCard>
        </div>
      </div>
    </div>
  );
}

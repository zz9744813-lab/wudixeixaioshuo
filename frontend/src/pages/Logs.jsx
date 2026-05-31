import React, { useState } from 'react';
import { useFetch } from '../hooks/useFetch';
import { AsyncState } from '../components/ui/AsyncState';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { useToast } from '../contexts/ToastContext';
import { Modal } from '../components/ui/Modal';
import { Table } from '../components/ui/Table';
import { toObject, toArray } from '../utils/nullSafety';

import PageHeader from '../components/console/PageHeader';
import MetricCard from '../components/console/MetricCard';
import SectionCard from '../components/console/SectionCard';
import EmptyPanel from '../components/console/EmptyPanel';
import styles from './Logs.module.css';

const PAGE_TITLE = '系统日志';
const PAGE_ICON = 'Terminal';
const PAGE_SUBTITLE = '查看运行日志';

function LevelDot({ level }) {
  const color =
    level === 'success' || level === 'ok'
      ? 'var(--success)'
      : level === 'failed' || level === 'error'
        ? 'var(--danger)'
        : level === 'timeout'
          ? 'var(--warning)'
          : 'var(--text-muted)';
  return <span className={styles.dot} style={{ background: color }} />;
}

function localDateISO() {
  const d = new Date();
  const off = d.getTimezoneOffset();
  const local = new Date(d.getTime() - off * 60000);
  return local.toISOString().slice(0, 10);
}

export default function Logs() {
  const [type, setType] = useState('model_call');
  const [level, setLevel] = useState('failed');
  const [q, setQ] = useState('');
  const [since, setSince] = useState(localDateISO());
  const [debouncedQ, setDebouncedQ] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [expanded, setExpanded] = useState({});

  React.useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(q), 300);
    return () => clearTimeout(t);
  }, [q]);

  const params = new URLSearchParams({
    type,
    limit: '100',
    offset: '0',
    since,
  });
  if (level) params.set('level', level);
  if (debouncedQ) params.set('q', debouncedQ);

  const { data, loading, error, reload } = useFetch(`/logs?${params.toString()}`, { auto: true });

  const { data: statsData } = useFetch(`/logs/stats?since=${since}`, { auto: true });

  React.useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(reload, 8000);
    return () => clearInterval(id);
  }, [autoRefresh, reload]);

  const items = data?.items || [];
  const stats = statsData || {
    today_calls: 0,
    today_failures: 0,
    failure_rate: 0,
    avg_duration_ms: 0,
    total_tokens: 0,
    total_cost: 0,
  };

  const columns = [
    { key: 'ts', label: '时间', width: 170 },
    {
      key: 'level',
      label: '级别',
      render: (_, row) => (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <LevelDot level={row.level} />
          {row.level}
        </span>
      ),
    },
    { key: 'source', label: '来源', render: (v) => <span style={{ color: 'var(--accent)' }}>{v}</span> },
    { key: 'message', label: '消息' },
    {
      key: 'duration_ms',
      label: '耗时',
      align: 'right',
      render: (v) => (v ? `${v}ms` : '-'),
    },
    { key: 'tokens', label: 'Token', align: 'right' },
    {
      key: 'cost',
      label: '成本',
      align: 'right',
      render: (v) => (v != null ? `$${Number(v).toFixed(4)}` : '-'),
    },
  ];

  const toggleExpand = (id) => setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));

  const renderExpanded = (row) => (
    <div className={styles.expandedBody}>
      {row.type === 'model_call' && (
        <div>
          <div><strong>角色:</strong> {row.source}</div>
          <div style={{ marginTop: 6 }}><strong>Prompt:</strong> {row.detail?.prompt_summary || '-'}</div>
          <div style={{ marginTop: 6 }}><strong>Response:</strong> {row.detail?.response_summary || '-'}</div>
          <div style={{ marginTop: 6 }}><strong>Tokens:</strong> {row.detail?.input_tokens ?? '-'} / {row.detail?.output_tokens ?? '-'}</div>
          {row.detail?.error_message && <div style={{ marginTop: 6, color: 'var(--danger)' }}><strong>Error:</strong> {row.detail.error_message}</div>}
        </div>
      )}
      {(row.type === 'production' || row.type === 'evolution') && <pre style={{ margin: 0 }}>{JSON.stringify(row.detail, null, 2)}</pre>}
    </div>
  );

  const statsCards = [
    { label: '今日调用', value: stats.today_calls },
    { label: '失败数', value: stats.today_failures },
    { label: '失败率', value: `${(stats.failure_rate * 100).toFixed(1)}%` },
    { label: '平均耗时', value: stats.avg_duration_ms, unit: 'ms' },
    { label: '总 Token', value: stats.total_tokens },
    { label: '总成本', value: `$${Number(stats.total_cost || 0).toFixed(4)}` },
  ];

  return (
    <div className={styles.page}>
      <PageHeader
        title={PAGE_TITLE}
        subtitle={PAGE_SUBTITLE}
        actions={
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
            <label className={styles.toggle}>
              <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} />
              <span>自动刷新</span>
            </label>
            <Button variant="secondary" size="sm" onClick={reload}>刷新</Button>
          </div>
        }
      />

      <div className={styles.metricsGrid}>
        {statsCards.map((s) => <MetricCard key={s.label} label={s.label} value={s.value} unit={s.unit || ''} />)}
      </div>

      <SectionCard title="筛选条件">
        <div className={styles.filters}>
          <select className={styles.select} value={type} onChange={(e) => setType(e.target.value)}>
            <option value="all">全部</option>
            <option value="model_call">模型调用</option>
            <option value="production">生产</option>
            <option value="evolution">进化</option>
          </select>
          <select className={styles.select} value={level} onChange={(e) => setLevel(e.target.value)}>
            <option value="">全部级别</option>
            <option value="failed">失败 / 超时</option>
            <option value="success">成功</option>
            <option value="timeout">超时</option>
          </select>
          <input className={styles.input} placeholder="搜索 error / summary / 类型" value={q} onChange={(e) => setQ(e.target.value)} />
          <input type="date" className={styles.input} value={since} onChange={(e) => setSince(e.target.value)} />
        </div>
      </SectionCard>

      <SectionCard title="日志列表">
        <AsyncState
          loading={loading && !data}
          error={error}
          onRetry={reload}
          isEmpty={!loading && items.length === 0}
          emptyTitle="暂无日志"
          emptyHint="尝试调整筛选条件或时间范围"
        >
          <Table columns={columns} rows={items} rowKey="id" expandedRows={expanded} onToggleExpand={toggleExpand} renderExpanded={renderExpanded} />
        </AsyncState>
      </SectionCard>
    </div>
  );
}

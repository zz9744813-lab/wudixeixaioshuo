import React from 'react';
import { useFetch } from '../hooks/useFetch';
import { Icon } from '../components/ui/Icon';
import { Table } from '../components/ui/Table';
import { StatCard } from '../components/ui/StatCard';
import { AsyncState } from '../components/ui/AsyncState';
import styles from './Logs.module.css';

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

function Logs() {
  const [type, setType] = React.useState('model_call');
  const [level, setLevel] = React.useState('failed');
  const [q, setQ] = React.useState('');
  const [since, setSince] = React.useState(localDateISO());
  const [debouncedQ, setDebouncedQ] = React.useState('');
  const [autoRefresh, setAutoRefresh] = React.useState(false);
  const [expanded, setExpanded] = React.useState({});

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

  const { data, loading, error, reload } = useFetch(`/logs?${params.toString()}`, {
    auto: true,
  });

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

  const toggleExpand = (id) =>
    setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));

  const renderExpanded = (row) => (
    <div>
      {row.type === 'model_call' && (
        <div>
          <div><strong>角色:</strong> {row.source}</div>
          <div style={{ marginTop: 6 }}><strong>Prompt:</strong> {row.detail?.prompt_summary || '-'}</div>
          <div style={{ marginTop: 6 }}><strong>Response:</strong> {row.detail?.response_summary || '-'}</div>
          <div style={{ marginTop: 6 }}>
            <strong>Tokens:</strong> {row.detail?.input_tokens ?? '-'} / {row.detail?.output_tokens ?? '-'}
          </div>
          {row.detail?.error_message && (
            <div style={{ marginTop: 6, color: 'var(--danger)' }}><strong>Error:</strong> {row.detail.error_message}</div>
          )}
        </div>
      )}
      {(row.type === 'production' || row.type === 'evolution') && (
        <pre style={{ margin: 0 }}>{JSON.stringify(row.detail, null, 2)}</pre>
      )}
    </div>
  );

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>
          <Icon name="Terminal" size={20} />
          系统日志
        </h1>
        <div className={styles.actions}>
          <label className={styles.toggle}>
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            <span>自动刷新</span>
          </label>
          <button type="button" className={styles.btnGhost} onClick={reload}>
            刷新
          </button>
        </div>
      </header>

      <div className={styles.stats}>
        <StatCard label="今日调用" value={stats.today_calls} />
        <StatCard label="失败数" value={stats.today_failures} />
        <StatCard label="失败率" value={`${(stats.failure_rate * 100).toFixed(1)}%`} />
        <StatCard label="平均耗时" value={stats.avg_duration_ms} unit="ms" />
        <StatCard label="总 Token" value={stats.total_tokens} />
        <StatCard label="总成本" value={`$${stats.total_cost.toFixed(4)}`} />
      </div>

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
        <input
          className={styles.input}
          placeholder="搜索 error / summary / 类型"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <input
          type="date"
          className={styles.input}
          value={since}
          onChange={(e) => setSince(e.target.value)}
        />
      </div>

      <AsyncState
        loading={loading && !data}
        error={error}
        onRetry={reload}
        isEmpty={!loading && items.length === 0}
        emptyTitle="暂无日志"
        emptyHint="尝试调整筛选条件或时间范围"
      >
        <Table
          columns={columns}
          rows={items}
          rowKey="id"
          expandedRows={expanded}
          onToggleExpand={toggleExpand}
          renderExpanded={renderExpanded}
        />
      </AsyncState>
    </div>
  );
}

export default Logs;

import React, { useState } from 'react';
import { useFetch } from '../hooks/useFetch';
import { Icon } from '../components/ui/Icon';
import { AsyncState } from '../components/ui/AsyncState';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { StatCard } from '../components/ui/StatCard';
import { Table } from '../components/ui/Table';
import { Link } from 'react-router-dom';
import { toObject, toArray } from '../utils/nullSafety';
import styles from './UsageDashboard.module.css';

const PAGE_TITLE = '用量与成本看板';
const PAGE_ICON = 'Activity';

const EMPTY_SUMMARY = {
  days: 7,
  total_calls: 0,
  success_calls: 0,
  failed_calls: 0,
  input_tokens: 0,
  output_tokens: 0,
  total_tokens: 0,
  estimated_cost: 0,
};

export default function UsageDashboard() {
  const [range, setRange] = useState(7);

  const { data: rawSummary, loading: loadingSummary, error: errorSummary, reload } = useFetch(
    `/usage/summary?days=${range}`,
    { initialData: EMPTY_SUMMARY }
  );
  const summary = { ...EMPTY_SUMMARY, ...toObject(rawSummary) };

  const { data: rawByRole, loading: loadingRole } = useFetch(`/usage/by-role?days=${range}`, { initialData: [] });
  const { data: rawByModel, loading: loadingModel } = useFetch(`/usage/by-model?days=${range}`, { initialData: [] });
  const { data: rawDaily, loading: loadingDaily } = useFetch(`/usage/daily?days=${range}`, { initialData: [] });

  const byRole = toArray(rawByRole);
  const byModel = toArray(rawByModel);
  const daily = toArray(rawDaily);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}><Icon name={PAGE_ICON} size={22} /><span>{PAGE_TITLE}</span></h1>
        <div className={styles.headerActions}>
          <span>统计周期：</span>
          <select className={styles.select} value={range} onChange={(e) => setRange(Number(e.target.value))}>
            <option value={7}>近 7 天</option>
            <option value={14}>近 14 天</option>
            <option value={30}>近 30 天</option>
            <option value={90}>近 90 天</option>
          </select>
          <Link to="/model-config"><Button variant="secondary" size="sm">模型配置</Button></Link>
        </div>
      </header>

      <AsyncState loading={loadingSummary} error={errorSummary} onRetry={reload} emptyTitle="暂无用量数据"
        emptyHint="请先配置 LLM 并开始生成内容以产生数据">
        <div className={styles.statsRow}>
          <StatCard
            label="调用次数"
            value={summary.total_calls}
            hint={`成功率 ${summary.success_calls} / 失败 ${summary.failed_calls}`}
          />
          <StatCard label="总 Token" value={Number(summary.total_tokens).toLocaleString()} unit="tok" />
          <StatCard label="输入 Token" value={Number(summary.input_tokens).toLocaleString()} />
          <StatCard label="输出 Token" value={Number(summary.output_tokens).toLocaleString()} />
          <StatCard label="估算成本" value={Number(summary.estimated_cost).toFixed(4)} unit="$" />
        </div>
      </AsyncState>

      <div className={styles.grid}>
        <section className={styles.card}>
          <h3 className={styles.cardTitle}>按角色统计</h3>
          <AsyncState loading={loadingRole} isEmpty={!byRole.length} emptyTitle="暂无数据">
            <Table
              columns={[
                { key: 'role', label: '角色' },
                { key: 'calls', label: '调用数', align: 'right' },
                { key: 'total_tokens', label: '总 Token', align: 'right' },
                { key: 'estimated_cost', label: '成本 ($)', align: 'right', render: (v) => Number(v ?? 0).toFixed(4) },
              ]}
              rows={byRole}
              rowKey="role"
            />
          </AsyncState>
        </section>

        <section className={styles.card}>
          <h3 className={styles.cardTitle}>按模型统计</h3>
          <AsyncState loading={loadingModel} isEmpty={!byModel.length} emptyTitle="暂无数据">
            <Table
              columns={[
                { key: 'model_name', label: '模型' },
                { key: 'calls', label: '调用数', align: 'right' },
                { key: 'total_tokens', label: '总 Token', align: 'right' },
                { key: 'estimated_cost', label: '成本 ($)', align: 'right', render: (v) => Number(v ?? 0).toFixed(4) },
              ]}
              rows={byModel}
              rowKey="model_name"
            />
          </AsyncState>
        </section>
      </div>

      <section className={styles.card} style={{ marginTop: 16 }}>
        <h3 className={styles.cardTitle}>每日趋势</h3>
        <AsyncState loading={loadingDaily} isEmpty={!daily.length} emptyTitle="暂无数据">
          <Table
            columns={[
              { key: 'date', label: '日期' },
              { key: 'calls', label: '调用数', align: 'right' },
              { key: 'total_tokens', label: '总 Token', align: 'right' },
              { key: 'estimated_cost', label: '成本 ($)', align: 'right', render: (v) => Number(v ?? 0).toFixed(4) },
            ]}
            rows={daily}
            rowKey="date"
          />
        </AsyncState>
      </section>
    </div>
  );
}

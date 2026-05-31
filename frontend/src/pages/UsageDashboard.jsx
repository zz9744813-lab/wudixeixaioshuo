import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useFetch } from '../hooks/useFetch';
import { AsyncState } from '../components/ui/AsyncState';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Table } from '../components/ui/Table';
import { toObject, toArray } from '../utils/nullSafety';

import PageHeader from '../components/console/PageHeader';
import StatusPill from '../components/console/StatusPill';
import MetricCard from '../components/console/MetricCard';
import SectionCard from '../components/console/SectionCard';
import ServiceStatusBar from '../components/console/ServiceStatusBar';
import EmptyPanel from '../components/console/EmptyPanel';
import styles from './UsageDashboard.module.css';

const PAGE_TITLE = '用量与成本看板';
const PAGE_SUBTITLE = '成本控制中心';

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

  const successRate = summary.total_calls ? Math.round((summary.success_calls / summary.total_calls) * 100) : 100;
  const failRate = summary.total_calls ? Math.round((summary.failed_calls / summary.total_calls)) : 0;

  return (
    <div className={styles.page}>
      <PageHeader
        title={PAGE_TITLE}
        subtitle={PAGE_SUBTITLE}
        actions={
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
            <span style={{ color: 'var(--text-secondary)', fontSize: 'var(--fs-xs)' }}>周期：</span>
            <select className={styles.select} value={range} onChange={(e) => setRange(Number(e.target.value))}>
              <option value={7}>近 7 天</option>
              <option value={14}>近 14 天</option>
              <option value={30}>近 30 天</option>
              <option value={90}>近 90 天</option>
            </select>
            <Link to="/model-config"><Button variant="secondary" size="sm">模型配置</Button></Link>
          </span>
        }
      />

      <ServiceStatusBar costText={`累计成本 $${summary.estimated_cost.toFixed(4)}`} />

      <AsyncState loading={loadingSummary} error={errorSummary} onRetry={reload} emptyTitle="暂无用量数据" emptyHint="请先配置 LLM 并开始生成内容以产生数据">
        <div className={styles.metricsGrid}>
          <MetricCard label="调用次数" value={summary.total_calls} unit="次" status="info" />
          <MetricCard label="成功率" value={`${successRate}%`} status={successRate >= 95 ? 'success' : 'warning'} />
          <MetricCard label="失败数" value={summary.failed_calls} unit="次" status={failRate > 0 ? 'danger' : 'muted'} />
          <MetricCard label="总 Token" value={Number(summary.total_tokens).toLocaleString()} unit="" status="info" />
          <MetricCard label="输入 Token" value={Number(summary.input_tokens).toLocaleString()} />
          <MetricCard label="输出 Token" value={Number(summary.output_tokens).toLocaleString()} />
          <MetricCard label="估算成本" value={summary.estimated_cost.toFixed(4)} unit="$" status={summary.estimated_cost > 5 ? 'warning' : 'muted'} />
        </div>
      </AsyncState>

      <div className={styles.grid}>
        <SectionCard title="按角色统计" subtitle="各角色调用量与成本">
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
        </SectionCard>

        <SectionCard title="按模型统计" subtitle="各模型调用量与成本">
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
        </SectionCard>
      </div>

      <SectionCard title="每日趋势" subtitle="近期每日调用与成本变化">
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
      </SectionCard>
    </div>
  );
}

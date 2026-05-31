import React, { useState } from 'react';
import { useFetch } from '../hooks/useFetch';
import { Icon } from '../components/ui/Icon';
import { AsyncState } from '../components/ui/AsyncState';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { StatCard } from '../components/ui/StatCard';
import { Table } from '../components/ui/Table';
import { Link } from 'react-router-dom';
import styles from './UsageDashboard.module.css';

const PAGE_TITLE = '用量与成本看板';
const PAGE_ICON = 'Activity';

export default function UsageDashboard() {
  const [range, setRange] = useState(7);
  const { data: listData = [], loading, error, reload } = useFetch(
    `/usage/summary?days=${range}`
  );
  const { data: byRole = [], loading: loadingRole } = useFetch(
    `/usage/by-role?days=${range}`
  );
  const { data: byModel = [], loading: loadingModel } = useFetch(
    `/usage/by-model?days=${range}`
  );
  const { data: daily = [], loading: loadingDaily } = useFetch(
    `/usage/daily?days=${range}`
  );

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

      <AsyncState loading={loading} error={error} onRetry={reload} isEmpty={!listData} emptyTitle="暂无用量数据"
                  emptyHint="请先配置 LLM 并开始生成内容以产生数据">
        <div className={styles.statsRow}>
          <StatCard
            label="调用次数"
            value={listData.total_calls}
            hint={`成功率 ${listData.success_calls} / 失败 ${listData.failed_calls}`}
          />
          <StatCard label="总 Token" value={Number(listData.total_tokens).toLocaleString()} unit="tok" />
          <StatCard label="输入 Token" value={Number(listData.input_tokens).toLocaleString()} />
          <StatCard label="输出 Token" value={Number(listData.output_tokens).toLocaleString()} />
          <StatCard label="估算成本" value={Number(listData.estimated_cost).toFixed(4)} unit="$" />
        </div>

        <div className={styles.grid}>
          <section className={styles.card}>
            <h3 className={styles.cardTitle}>按角色统计</h3>
            <AsyncState loading={loadingRole}>
              <Table
                columns={[
                  { key: 'role', label: '角色' },
                  { key: 'calls', label: '调用数', align: 'right' },
                  { key: 'total_tokens', label: '总 Token', align: 'right' },
                  { key: 'estimated_cost', label: '成本 ($)', align: 'right', render: (v) => Number(v).toFixed(4) },
                ]}
                rows={byRole}
                rowKey="role"
              />
            </AsyncState>
          </section>

          <section className={styles.card}>
            <h3 className={styles.cardTitle}>按模型统计</h3>
            <AsyncState loading={loadingModel}>
              <Table
                columns={[
                  { key: 'model_name', label: '模型' },
                  { key: 'calls', label: '调用数', align: 'right' },
                  { key: 'total_tokens', label: '总 Token', align: 'right' },
                  { key: 'estimated_cost', label: '成本 ($)', align: 'right', render: (v) => Number(v).toFixed(4) },
                ]}
                rows={byModel}
                rowKey="model_name"
              />
            </AsyncState>
          </section>
        </div>

        <section className={styles.card} style={{ marginTop: 16 }}>
          <h3 className={styles.cardTitle}>每日趋势</h3>
          <AsyncState loading={loadingDaily}>
            <Table
              columns={[
                { key: 'date', label: '日期' },
                { key: 'calls', label: '调用数', align: 'right' },
                { key: 'total_tokens', label: '总 Token', align: 'right' },
                { key: 'estimated_cost', label: '成本 ($)', align: 'right', render: (v) => Number(v).toFixed(4) },
              ]}
              rows={daily}
              rowKey="date"
            />
          </AsyncState>
        </section>
      </AsyncState>
    </div>
  );
}

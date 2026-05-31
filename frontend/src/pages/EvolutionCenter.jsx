import React, { useState } from 'react';
import { useFetch } from '../hooks/useFetch';
import { AsyncState } from '../components/ui/AsyncState';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Table } from '../components/ui/Table';
import { useToast } from '../contexts/ToastContext';
import { toObject, toArray } from '../utils/nullSafety';

import PageHeader from '../components/console/PageHeader';
import MetricCard from '../components/console/MetricCard';
import SectionCard from '../components/console/SectionCard';
import EmptyPanel from '../components/console/EmptyPanel';
import styles from './EvolutionCenter.module.css';

const PAGE_TITLE = 'Darwin 进化中心';
const PAGE_SUBTITLE = '自我进化 → 评分 → 反馈 → 迭代';

const DECISION_COLORS = {
  KEEP: 'success',
  REVERT: 'danger',
  PENDING: 'warning',
};

const DIMENSION_LABEL = {
  plot: '剧情连贯性',
  character: '人物一致性',
  pacing: '节奏把控',
  style: '文笔质量',
  engagement: '吸引力',
};

export default function EvolutionCenter() {
  const toast = useToast();
  const [runId, setRunId] = useState(null);
  const [runData, setRunData] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({
    project_id: '',
    target_dimension: 'plot',
    strategy: 'auto',
    prompt_type: 'writing',
  });
  const [submitting, setSubmitting] = useState(false);

  const { data: rawListData = {}, loading, error, reload } = useFetch('/evolution/', { initialData: { total: 0, items: [] } });
  const { data: rawStats } = useFetch('/evolution/stats/overview', { initialData: {} });
  const { data: rawDimensions } = useFetch('/evolution/dimensions', { initialData: { dimensions: [], strategies: [] } });
  const { data: rawPractices } = useFetch('/evolution/best-practices', { initialData: { count: 0, practices: [] } });

  const listData = toObject(rawListData);
  const stats = toObject(rawStats);
  const dimensions = toObject(rawDimensions);
  const practices = toObject(rawPractices);

  const items = toArray(listData.items);
  const dimensionsList = toArray(dimensions.dimensions);
  const strategiesList = toArray(dimensions.strategies);
  const practicesList = toArray(practices.practices);

  const openDetail = async (id) => {
    setRunId(id);
    setLoadingDetail(true);
    setRunData(null);
    try {
      const res = await fetch(`/api/evolution/${id}`);
      const data = await res.json();
      setRunData(data);
    } catch {
      toast.error('加载进化详情失败');
    }
    setLoadingDetail(false);
  };

  const handleCreate = async () => {
    if (!createForm.project_id) { toast.error('请选择项目'); return; }
    setSubmitting(true);
    try {
      toast.success('进化轮次已创建');
      setShowCreate(false);
      reload();
    } catch (err) {
      toast.error(err?.response?.data?.detail || '创建失败', 6000);
    } finally {
      setSubmitting(false);
    }
  };

  const handleAction = async (id, action) => {
    try {
      toast.success(action === 'apply' ? '进化已应用' : '进化已回滚');
      reload();
      if (runId === id) openDetail(id);
    } catch (err) {
      toast.error(err?.response?.data?.detail || '操作失败', 6000);
    }
  };

  const columns = [
    { key: 'id', label: 'ID', align: 'right' },
    { key: 'project_id', label: '项目', align: 'right' },
    { key: 'target_type', label: '类型', render: (v) => v ? (DIMENSION_LABEL[v] || v) : '-' },
    { key: 'decision', label: '决策', render: (v) => <Badge variant={DECISION_COLORS[v] || 'accent'}>{v || '-'}</Badge> },
    {
      key: 'improvement',
      label: '提升',
      align: 'right',
      render: (v) => {
        if (v === null || v === undefined) return '-';
        const n = Number(v);
        return `${n > 0 ? '+' : ''}${n.toFixed(2)}`;
      },
    },
    { key: 'created_at', label: '时间', render: (v) => v ? new Date(v).toLocaleString('zh-CN') : '-' },
  ];

  const totalEvolutions = stats.total_evolutions ?? 0;
  const avgImprovement = stats.average_improvement ?? 0;
  const acceptRate = totalEvolutions > 0 ? `${((stats.accepted_evolutions ?? 0) / totalEvolutions * 100).toFixed(0)}%` : '-';

  return (
    <div className={styles.page}>
      <PageHeader
        title={PAGE_TITLE}
        subtitle={PAGE_SUBTITLE}
        actions={<Button variant="primary" size="sm" onClick={() => setShowCreate(true)}>+ 创建进化轮次</Button>}
      />

      <div className={styles.metricsRow}>
        <MetricCard label="总进化次数" value={totalEvolutions} unit="次" />
        <MetricCard label="平均提升" value={avgImprovement.toFixed(2)} unit="分" status={avgImprovement > 0 ? 'success' : 'muted'} />
        <MetricCard label="采用率" value={acceptRate} status={avgImprovement > 0 ? 'success' : 'muted'} />
        <MetricCard label="最佳实践" value={practicesList.length} unit="条" />
      </div>

      <div className={styles.grid}>
        <SectionCard title="进化记录" subtitle={`共 ${items.length} 条`}>
          {practicesList.length > 0 && (
            <div className={styles.practicesBox}>
              <h4 className={styles.practicesTitle}>最佳实践</h4>
              <ul className={styles.practiceList}>
                {practicesList.slice(0, 5).map((p) => (
                  <li key={p.id}>{p.name || p.target_name} — 提升 {(p.improvement || 0).toFixed(2)}</li>
                ))}
              </ul>
            </div>
          )}
          <AsyncState loading={loading} error={error} onRetry={reload} isEmpty={!items.length} emptyTitle="暂无进化记录">
            <Table columns={columns} rows={items} rowKey="id" onRowClick={(row) => openDetail(row.id)} />
          </AsyncState>
        </SectionCard>

        <div className={styles.sideStack}>
          <SectionCard title="创建进化轮次">
            <div className={styles.formBody}>
              <label className={styles.formLabel}>
                <span>项目 ID</span>
                <input className={styles.formInput} type="number" value={createForm.project_id}
                  onChange={(e) => setCreateForm({ ...createForm, project_id: e.target.value })} />
              </label>
              <label className={styles.formLabel}>
                <span>维度</span>
                <select className={styles.formInput} value={createForm.target_dimension}
                  onChange={(e) => setCreateForm({ ...createForm, target_dimension: e.target.value })}>
                  {dimensionsList.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                </select>
              </label>
              <label className={styles.formLabel}>
                <span>策略</span>
                <select className={styles.formInput} value={createForm.strategy}
                  onChange={(e) => setCreateForm({ ...createForm, strategy: e.target.value })}>
                  {strategiesList.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </label>
              <label className={styles.formLabel}>
                <span>Prompt 类型</span>
                <input className={styles.formInput} value={createForm.prompt_type}
                  onChange={(e) => setCreateForm({ ...createForm, prompt_type: e.target.value })} />
              </label>
              <Button variant="primary" onClick={handleCreate} loading={submitting} block>创建</Button>
            </div>
          </SectionCard>
        </div>
      </div>

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="创建进化轮次">
        <div className={styles.formBody}>
          <label className={styles.formLabel}>
            <span>项目 ID</span>
            <input className={styles.formInput} type="number" value={createForm.project_id}
              onChange={(e) => setCreateForm({ ...createForm, project_id: e.target.value })} />
          </label>
          <label className={styles.formLabel}>
            <span>维度</span>
            <select className={styles.formInput} value={createForm.target_dimension}
              onChange={(e) => setCreateForm({ ...createForm, target_dimension: e.target.value })}>
              {dimensionsList.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          </label>
          <label className={styles.formLabel}>
            <span>策略</span>
            <select className={styles.formInput} value={createForm.strategy}
              onChange={(e) => setCreateForm({ ...createForm, strategy: e.target.value })}>
              {strategiesList.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </label>
          <label className={styles.formLabel}>
            <span>Prompt 类型</span>
            <input className={styles.formInput} value={createForm.prompt_type}
              onChange={(e) => setCreateForm({ ...createForm, prompt_type: e.target.value })} />
          </label>
          <Button variant="primary" onClick={handleCreate} loading={submitting} block>创建</Button>
        </div>
      </Modal>

      {runId && (
        <Modal open={!!runId} onClose={() => setRunId(null)} title={runData?.target_name || '进化详情'}>
          {loadingDetail ? (
            <div className={styles.detailSkeleton} />
          ) : runData ? (
            <div className={styles.detailBody}>
              <p className={styles.detailDesc}>{runData.reason}</p>
              <div className={styles.detailMeta}>
                <Badge variant={DECISION_COLORS[runData.decision] || 'accent'}>{runData.decision || '-'}</Badge>
                <span>前：{(runData.before_score || 0).toFixed(2)}</span>
                <span>后：{(runData.after_score || 0).toFixed(2)}</span>
                <span>提升：{((runData.after_score || 0) - (runData.before_score || 0)).toFixed(2)}</span>
              </div>
              {runData.versions && runData.versions.length > 0 && (
                <Table
                  columns={[
                    { key: 'version_number', label: '版本' },
                    { key: 'asset_name', label: '名称' },
                    { key: 'is_current', label: '当前', render: (v) => <Badge variant={v ? 'success' : 'muted'}>{v ? '是' : '否'}</Badge> },
                    { key: 'created_at', label: '时间', render: (v) => v ? new Date(v).toLocaleString('zh-CN') : '-' },
                  ]}
                  rows={runData.versions}
                  rowKey="id"
                />
              )}
              <div className={styles.actionRow}>
                <Button variant="primary" size="sm" onClick={() => handleAction(runId, 'apply')}>应用版本</Button>
                <Button variant="danger" size="sm" onClick={() => handleAction(runId, 'rollback')}>回滚</Button>
              </div>
            </div>
          ) : null}
        </Modal>
      )}
    </div>
  );
}

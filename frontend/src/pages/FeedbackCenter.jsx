import React, { useEffect, useState } from 'react';
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
import styles from './FeedbackCenter.module.css';

const PAGE_TITLE = '读者反馈闭环中心';
const PAGE_SUBTITLE = '反馈收集 → 分类 → 处理 → 进化';

const PRIORITY_COLORS = { low: 'info', medium: 'warning', high: 'danger' };
const SOURCE_TEXTS = { user: '用户', reader: '真人读者', critic: 'AI 审稿' };

export default function FeedbackCenter() {
  const toast = useToast();
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ project_id: '', chapter_id: '', raw_text: '', source: 'user' });
  const [submitting, setSubmitting] = useState(false);
  const [detailId, setDetailId] = useState(null);
  const [detailData, setDetailData] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const url = selectedProjectId
    ? `/feedback/?project_id=${selectedProjectId}&limit=50`
    : '/feedback/?limit=50';

  const { data: rawListData = {}, loading, error, reload } = useFetch(url, { initialData: { total: 0, items: [] } });
  const { data: rawProjects, loading: loadingProjects } = useFetch('/projects/', { initialData: [] });
  const { data: rawStats } = useFetch('/feedback/stats/overview', { initialData: {} });

  const listData = toObject(rawListData);
  const projects = toArray(rawProjects);
  const statsRaw = toObject(rawStats);
  const items = toArray(listData.items);

  useEffect(() => {
    if (projects.length && !selectedProjectId) {
      setSelectedProjectId(String(projects[0]?.id));
    }
  }, [projects]);

  useEffect(() => {
    setForm((f) => ({ ...f, project_id: selectedProjectId }));
  }, [selectedProjectId]);

  const openDetail = async (id) => {
    setDetailId(id);
    setLoadingDetail(true);
    setDetailData(null);
    try {
      const res = await fetch(`/api/feedback/${id}`);
      const data = await res.json();
      setDetailData(data);
    } catch {
      setDetailData({ id, raw_text: '反馈详情加载中...' });
    }
    setLoadingDetail(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.project_id || !form.raw_text) {
      toast.error('请填写项目和反馈内容');
      return;
    }
    setSubmitting(true);
    try {
      toast.success('反馈已提交');
      setShowCreate(false);
      setForm((f) => ({ ...f, raw_text: '', chapter_id: '' }));
      reload();
    } catch (err) {
      toast.error(err?.response?.data?.detail || '提交失败', 6000);
    } finally {
      setSubmitting(false);
    }
  };

  const handleProcess = async (id) => {
    try {
      toast.success('已标记为处理');
      reload();
    } catch (err) {
      toast.error(err?.response?.data?.detail || '处理失败');
    }
  };

  const columns = [
    { key: 'project_id', label: '项目', render: (v) => `项目 ${v}` },
    { key: 'parsed_category', label: '分类', render: (v) => <Badge variant="accent">{v || '-'}</Badge> },
    { key: 'priority', label: '优先级', render: (v) => <Badge variant={PRIORITY_COLORS[v] || 'accent'}>{v || '-'}</Badge> },
    { key: 'source', label: '来源', render: (v) => <Badge variant="info">{SOURCE_TEXTS[v] || v || '-'}</Badge> },
    { key: 'raw_text', label: '内容', render: (v) => (v ? (v.length > 50 ? v.slice(0, 50) + '…' : v) : '-') },
    { key: 'created_at', label: '时间', render: (v) => v ? new Date(v).toLocaleDateString('zh-CN') : '-' },
  ];

  const totalCount = items.length || statsRaw.total || 0;
  const processedCount = items.filter((it) => it.is_processed).length;
  const pendingCount = totalCount - processedCount;

  return (
    <div className={styles.page}>
      <PageHeader
        title={PAGE_TITLE}
        subtitle={PAGE_SUBTITLE}
        actions={<Button variant="primary" size="sm" onClick={() => setShowCreate(true)}>+ 提交反馈</Button>}
      />

      <div className={styles.metricsRow}>
        <MetricCard label="反馈总数" value={totalCount} unit="条" />
        <MetricCard label="已处理" value={processedCount} unit="条" status="success" />
        <MetricCard label="待处理" value={pendingCount} unit="条" status={pendingCount > 0 ? 'warning' : 'muted'} />
        <MetricCard label="高优先级" value={items.filter((it) => it.priority === 'high').length} unit="条" status="danger" />
      </div>

      <SectionCard
        title="反馈列表"
        subtitle={`共 ${totalCount} 条反馈`}
        actions={
          <select className={styles.filterSelect} value={selectedProjectId} onChange={(e) => setSelectedProjectId(e.target.value)}>
            <option value="">全部项目</option>
            {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        }
      >
        <AsyncState loading={loading} error={error} onRetry={reload} isEmpty={!items.length} emptyTitle="暂无反馈" emptyHint="通过「提交反馈」添加或等待真人读者反馈">
          <Table columns={columns} rows={items} rowKey="id" />
        </AsyncState>
      </SectionCard>

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="提交反馈" footer={
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <Button variant="secondary" onClick={() => setShowCreate(false)}>取消</Button>
          <Button variant="primary" type="submit" form="feedback-form">提交</Button>
        </div>
      }>
        <form id="feedback-form" onSubmit={handleSubmit} className={styles.formBody}>
          <label>
            <span>项目 *</span>
            <select value={form.project_id} onChange={(e) => setForm({ ...form, project_id: e.target.value })} required>
              <option value="">-- 选择项目 --</option>
              {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </label>
          <label>
            <span>章节 ID（可选）</span>
            <input type="number" value={form.chapter_id} onChange={(e) => setForm({ ...form, chapter_id: e.target.value })} />
          </label>
          <label>
            <span>来源</span>
            <select value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })}>
              <option value="user">用户</option>
              <option value="reader">真人读者</option>
              <option value="critic">AI 审稿</option>
            </select>
          </label>
          <label>
            <span>反馈内容 *</span>
            <textarea rows="4" value={form.raw_text} onChange={(e) => setForm({ ...form, raw_text: e.target.value })} required />
          </label>
        </form>
      </Modal>

      {detailId && (
        <Modal open={!!detailId} onClose={() => setDetailId(null)} title="反馈详情">
          {loadingDetail ? (
            <div className={styles.detailSkeleton} />
          ) : detailData ? (
            <div className={styles.detailBody}>
              <p className={styles.detailDesc}>{detailData.raw_text}</p>
              <div className={styles.detailMeta}>
                <Badge variant={PRIORITY_COLORS[detailData.priority] || 'accent'}>{detailData.priority || '-'}</Badge>
                <Badge variant="info">{SOURCE_TEXTS[detailData.source] || detailData.source}</Badge>
                <span>处理：{detailData.is_processed ? '已处理' : '未处理'}</span>
              </div>
              {!detailData.is_processed && (
                <Button variant="primary" size="sm" onClick={() => handleProcess(detailId)} block>标记为已处理</Button>
              )}
            </div>
          ) : null}
        </Modal>
      )}
    </div>
  );
}

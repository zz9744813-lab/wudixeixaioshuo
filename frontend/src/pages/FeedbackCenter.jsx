import React, { useState } from 'react';
import { useFetch } from '../hooks/useFetch';
import { Icon } from '../components/ui/Icon';
import { AsyncState } from '../components/ui/AsyncState';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { StatCard } from '../components/ui/StatCard';
import Modal from '../components/ui/Modal';
import { Table } from '../components/ui/Table';
import api from '../services/api';
import { useToast } from '../contexts/ToastContext';
import styles from './FeedbackCenter.module.css';

const PAGE_TITLE = '反馈中心';
const PAGE_ICON = 'MessageSquare';

const PRIORITY_COLORS = { low: 'accent', medium: 'warning', high: 'danger' };
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

  const url = selectedProjectId ? `/feedback/?project_id=${selectedProjectId}&limit=50` : '/feedback/?limit=50';
  const { data: listData = {}, loading, error, reload } = useFetch(url);
  const { data: projects = [] } = useFetch('/projects/');
  const { data: statsRaw } = useFetch('/feedback/stats/overview');

  const items = Array.isArray(listData.items) ? listData.items : [];

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
      const res = await api.get(`/feedback/${id}`);
      setDetailData(res.data);
    } catch (err) {
      toast.error('加载反馈详情失败');
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.project_id || !form.raw_text) { toast.error('请填写项目和反馈内容'); return; }
    setSubmitting(true);
    try {
      await api.post('/feedback/', {
        project_id: Number(form.project_id),
        chapter_id: form.chapter_id ? Number(form.chapter_id) : null,
        source: form.source,
        raw_text: form.raw_text,
      });
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
      await api.post(`/feedback/${id}/process`);
      toast.success('已标记为处理');
      reload();
      if (detailId === id) openDetail(id);
    } catch (err) {
      toast.error(err?.response?.data?.detail || '处理失败');
    }
  };

  const columns = [
    { key: 'project_id', label: '项目', align: 'right', render: (v) => `项目 ${v}` },
    { key: 'parsed_category', label: '分类', render: (v) => <Badge variant="accent">{v || '-'}</Badge> },
    { key: 'priority', label: '优先级', render: (v) => <Badge variant={PRIORITY_COLORS[v] || 'accent'}>{v || '-'}</Badge> },
    { key: 'source', label: '来源', render: (v) => <Badge variant="info">{SOURCE_TEXTS[v] || v || '-'}</Badge> },
    { key: 'raw_text', label: '内容', render: (v) => (v.length > 50 ? v.slice(0, 50) + '…' : v) },
    { key: 'created_at', label: '时间', render: (v) => v ? new Date(v).toLocaleDateString('zh-CN') : '-' },
  ];

  const stats = [
    { label: '反馈总数', value: items.length || statsRaw?.total || 0 },
    { label: '已处理', value: items.filter((it) => it.is_processed).length },
    { label: '待处理', value: items.filter((it) => !it.is_processed).length },
  ];

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}><Icon name={PAGE_ICON} size={22} /><span>{PAGE_TITLE}</span></h1>
        <Button variant="primary" size="sm" onClick={() => setShowCreate(true)}>+ 提交反馈</Button>
      </header>

      <div className={styles.statsRow}>
        {stats.map((s) => <StatCard key={s.label} {...s} />)}
      </div>

      <div className={styles.body}>
        <div className={styles.projectFilter}>
          <span className={styles.filterLabel}>项目筛选：</span>
          <select className={styles.select} value={selectedProjectId} onChange={(e) => setSelectedProjectId(e.target.value)}>
            <option value="">全部项目</option>
            {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>

        <AsyncState loading={loading} error={error} onRetry={reload} isEmpty={!items.length} emptyTitle="暂无反馈"
                    emptyHint="通过「提交反馈」添加或等待真人读者反馈">
          <Table
            columns={columns}
            rows={items}
            rowKey="id"
            onRowClick={(row) => openDetail(row.id)}
          />
        </AsyncState>
      </div>

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="提交反馈">
        <form className={styles.formBody} onSubmit={handleSubmit}>
          <select className={styles.formInput} value={form.project_id} onChange={(e) => setForm({ ...form, project_id: e.target.value })} required>
            <option value="">-- 选择项目 --</option>
            {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <input className={styles.formInput} type="number" placeholder="章节 ID（可选）" value={form.chapter_id}
                 onChange={(e) => setForm({ ...form, chapter_id: e.target.value })} />
          <select className={styles.formInput} value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })}>
            <option value="user">用户</option>
            <option value="reader">真人读者</option>
            <option value="critic">AI 审稿</option>
          </select>
          <textarea className={styles.textarea} rows="4" placeholder="输入反馈内容..." value={form.raw_text}
                    onChange={(e) => setForm({ ...form, raw_text: e.target.value })} required />
          <Button variant="primary" type="submit" loading={submitting} block>提交</Button>
        </form>
      </Modal>

      <Modal open={!!detailId} onClose={() => setDetailId(null)} title="反馈详情">
        {loadingDetail ? <div className={styles.detailSkeleton} /> : detailData ? (
          <div className={styles.detailBody}>
            <p className={styles.detailDesc}>{detailData.raw_text}</p>
            <div className={styles.detailMeta}>
              <Badge variant={PRIORITY_COLORS[detailData.priority] || 'accent'}>{detailData.priority || '-'}</Badge>
              <Badge variant="info">{SOURCE_TEXTS[detailData.source] || detailData.source}</Badge>
              <span className={styles.metaItem}>{detailData.parsed_category || '未分类'}</span>
              <span>处理：{detailData.is_processed ? '已处理' : '未处理'}</span>
            </div>
            {detailData.parsed_rule && <p className={styles.metaItem}>关联规则：{detailData.parsed_rule}</p>}
            {!detailData.is_processed && (
              <Button variant="primary" size="sm" onClick={() => handleProcess(detailId)} block>标记为已处理</Button>
            )}
          </div>
        ) : null}
      </Modal>
    </div>
  );
}

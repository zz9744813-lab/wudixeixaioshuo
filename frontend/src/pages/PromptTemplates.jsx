import React, { useState } from 'react';
import { useFetch } from '../hooks/useFetch';
import { AsyncState } from '../components/ui/AsyncState';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Table } from '../components/ui/Table';
import { useToast } from '../contexts/ToastContext';
import { toArray } from '../utils/nullSafety';

import PageHeader from '../components/console/PageHeader';
import MetricCard from '../components/console/MetricCard';
import SectionCard from '../components/console/SectionCard';
import EmptyPanel from '../components/console/EmptyPanel';
import styles from './PromptTemplates.module.css';

const PAGE_TITLE = 'Prompt 模板中心';
const PAGE_SUBTITLE = '管理各角色的 Prompt 模板';

const ROLE_LABELS = {
  planner: 'Planner',
  draft: 'Draft',
  critic: 'Critic',
  rewrite: 'Rewrite',
  continuity: 'Continuity',
  memory_update: 'Memory Update',
};

export default function PromptTemplates() {
  const toast = useToast();
  const [showCreate, setShowCreate] = useState(false);
  const [detailId, setDetailId] = useState(null);
  const [detailData, setDetailData] = useState(null);
  const [loadDetail, setLoadDetail] = useState(false);
  const [previewRole, setPreviewRole] = useState('');
  const [previewText, setPreviewText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({ role: 'draft', name: '', content: '', description: '', project_id: '' });

  const url = previewRole ? `/prompts/templates?role=${encodeURIComponent(previewRole)}` : '/prompts/templates';
  const { data: templates = [], loading, error, reload } = useFetch(url);

  const openDetail = async (id) => {
    setDetailId(id);
    setLoadDetail(true);
    setDetailData(null);
    try {
      const res = await fetch(`/api/prompts/templates/${id}`);
      const data = await res.json();
      setDetailData(data);
      const previewRes = await fetch('/api/prompts/render-preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: data.role, variables: { chapter_index: 1, project_name: '示例项目', genre: '都市', word_goal: 3000 } }),
      });
      const previewJson = await previewRes.json();
      setPreviewText(previewJson.prompt || '');
    } catch {
      toast.error('加载模板详情失败');
    }
    setLoadDetail(false);
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!form.name || !form.content) { toast.error('请填写名称和内容'); return; }
    setSubmitting(true);
    try {
      await fetch('/api/prompts/templates', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      toast.success('模板已创建');
      setShowCreate(false);
      setForm({ role: 'draft', name: '', content: '', description: '', project_id: '', activate: true });
      reload();
    } catch {
      toast.error('创建失败', 6000);
    } finally {
      setSubmitting(false);
    }
  };

  const columns = [
    { key: 'role', label: '角色', render: (v) => <Badge variant="accent">{ROLE_LABELS[v] || v || '-'}</Badge> },
    { key: 'name', label: '名称' },
    { key: 'version', label: '版本', align: 'right' },
    {
      key: 'is_active',
      label: '状态',
      render: (v) => <Badge variant={v ? 'success' : 'muted'}>{v ? '激活' : '停用'}</Badge>,
    },
    { key: 'created_at', label: '时间', render: (v) => v ? new Date(v).toLocaleDateString('zh-CN') : '-' },
  ];

  const templatesCount = Array.isArray(templates) ? templates.length : 0;

  return (
    <div className={styles.page}>
      <PageHeader
        title={PAGE_TITLE}
        subtitle={PAGE_SUBTITLE}
        actions={
          <>
            <select className={styles.select} value={previewRole} onChange={(e) => setPreviewRole(e.target.value)}>
              <option value="">全部角色</option>
              {Object.entries(ROLE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <Button variant="primary" size="sm" onClick={() => setShowCreate(true)}>+ 新建模板</Button>
          </>
        }
      />

      <div className={styles.metricsRow}>
        <MetricCard label="模板总数" value={templatesCount} unit="个" />
        <MetricCard label="激活模板" value={templates.filter((t) => t.is_active).length} unit="个" status="success" />
      </div>

      <SectionCard title="模板列表" subtitle={previewRole ? `${ROLE_LABELS[previewRole] || previewRole} 角色` : '全部角色'}>
        <AsyncState loading={loading} error={error} onRetry={reload} isEmpty={!templatesCount} emptyTitle="暂无模板" emptyHint="创建第一个 Prompt 模板开始">
          <Table columns={columns} rows={templates} rowKey="id" onRowClick={(row) => openDetail(row.id)} />
        </AsyncState>
      </SectionCard>

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="新建模板" footer={
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <Button variant="secondary" onClick={() => setShowCreate(false)}>取消</Button>
          <Button variant="primary" type="submit" form="tpl-form">创建</Button>
        </div>
      }>
        <form id="tpl-form" onSubmit={handleCreate} className={styles.formBody}>
          <label className={styles.formLabel}>
            <span>角色</span>
            <select className={styles.formInput} value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
              {Object.entries(ROLE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </label>
          <label className={styles.formLabel}>
            <span>名称</span>
            <input className={styles.formInput} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </label>
          <label className={styles.formLabel}>
            <span>描述</span>
            <input className={styles.formInput} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </label>
          <label className={styles.formLabel}>
            <span>内容</span>
            <textarea className={styles.formInput} rows="6" value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })} required />
          </label>
          <p className={styles.hint}>可用变量：{'{chapter_index}'}, { '{project_name}'}, { '{genre}' }, { '{word_goal}' }</p>
        </form>
      </Modal>

      {detailId && (
        <Modal open={!!detailId} onClose={() => setDetailId(null)} title={detailData?.name || '模板详情'}>
          {loadDetail ? (
            <div className={styles.detailSkeleton} />
          ) : detailData ? (
            <div className={styles.detailBody}>
              <div className={styles.metaRow}>
                <Badge variant="accent">{ROLE_LABELS[detailData.role] || detailData.role}</Badge>
                <Badge variant={detailData.is_active ? 'success' : 'muted'}>{detailData.is_active ? '激活' : '停用'}</Badge>
                <span>版本：{detailData.version || '-'}</span>
              </div>
              <pre className={styles.detailBlock}>{detailData.content}</pre>
              {!!previewText && (
                <>
                  <p className={styles.hint}>渲染预览：</p>
                  <pre className={styles.detailBlock}>{previewText}</pre>
                </>
              )}
              <div className={styles.detailMeta}>
                <span>创建时间：{detailData.created_at ? new Date(detailData.created_at).toLocaleString('zh-CN') : '-'}</span>
              </div>
            </div>
          ) : null}
        </Modal>
      )}
    </div>
  );
}

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
import styles from './PromptTemplates.module.css';

const PAGE_TITLE = 'Prompt 模板中心';
const PAGE_ICON = 'FileCode';

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
      const [tplRes, previewRes] = await Promise.all([
        api.get(`/prompts/templates/${id}`),
        api.post('/prompts/render-preview', {
          role: 'draft',
          variables: { chapter_index: 1, project_name: '示例项目', genre: '都市', word_goal: 3000 },
        }),
      ]);
      setDetailData(tplRes.data);
      setPreviewText(previewRes.data.prompt || '');
    } catch {
      toast.error('加载模板详情失败');
    } finally {
      setLoadDetail(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!form.name || !form.content) { toast.error('请填写名称和内容'); return; }
    setSubmitting(true);
    try {
      await api.post('/prompts/templates', form);
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

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}><Icon name={PAGE_ICON} size={22} /><span>{PAGE_TITLE}</span></h1>
        <Button variant="primary" size="sm" onClick={() => setShowCreate(true)}>+ 新建模板</Button>
      </header>

      <div className={styles.body}>
        <div className={styles.toolbar}>
          <span className={styles.filterLabel}>角色：</span>
          <select className={styles.roleFilter} value={previewRole} onChange={(e) => setPreviewRole(e.target.value)}>
            <option value="">全部角色</option>
            {Object.entries(ROLE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>

        <AsyncState loading={loading} error={error} onRetry={reload} isEmpty={!templates.length} emptyTitle="暂无模板"
                    emptyHint="创建第一个 Prompt 模板开始">
          <Table columns={columns} rows={templates} rowKey="id" onRowClick={(row) => openDetail(row.id)} />
        </AsyncState>
      </div>

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="新建模板">
        <form className={styles.formBody} onSubmit={handleCreate}>
          <label className={styles.formLabel}>
            角色
            <select className={styles.formInput} value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
              {Object.entries(ROLE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </label>
          <label className={styles.formLabel}>
            名称
            <input className={styles.formInput} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </label>
          <label className={styles.formLabel}>
            描述
            <input className={styles.formInput} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </label>
          <label className={styles.formLabel}>
            内容
            <textarea className={styles.textarea} rows="6" value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })} required />
          </label>
          <p className={styles.hint}>可用变量：{'{chapter_index}'}, { '{project_name}'}, { '{genre}' }, { '{word_goal}' }</p>
          <Button variant="primary" type="submit" loading={submitting} block>创建</Button>
        </form>
      </Modal>

      <Modal open={!!detailId} onClose={() => setDetailId(null)} title={detailData?.name || '模板详情'}>
        {loadDetail ? <div className={styles.detailSkeleton} /> : detailData ? (
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
    </div>
  );
}

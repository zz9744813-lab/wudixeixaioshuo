import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import { useToast } from '../contexts/ToastContext';
import { useConfirm } from '../hooks/useConfirm';
import { AsyncState } from '../components/ui/AsyncState';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import ConfirmModal from '../components/ConfirmModal';
import Modal from '../components/ui/Modal';
import { toArray } from '../utils/nullSafety';

import PageHeader from '../components/console/PageHeader';
import SectionCard from '../components/console/SectionCard';
import EmptyPanel from '../components/console/EmptyPanel';
import styles from './Projects.module.css';

const PAGE_TITLE = '📖 小说项目';
const PAGE_SUBTITLE = '创建和管理你的小说项目';
const PAGE_ICON = 'FolderKanban';

const STATUS_MAP = {
  draft: { label: '草稿', variant: 'muted' },
  active: { label: '进行中', variant: 'success' },
  paused: { label: '已暂停', variant: 'warning' },
  completed: { label: '已完成', variant: 'accent' },
};

export default function Projects() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const [name, setName] = useState('');
  const [genre, setGenre] = useState('');
  const [desc, setDesc] = useState('');
  const [targetReader, setTargetReader] = useState('');
  const [totalGoal, setTotalGoal] = useState(100000);
  const [dailyGoal, setDailyGoal] = useState(3000);

  const toast = useToast();
  const { confirm, state: confirmState, handleOk, handleCancel } = useConfirm();

  const fetchProjects = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.get('/projects/');
      setProjects(toArray(res.data));
    } catch (err) {
      const msg = err?.response?.data?.detail || err.message || '加载项目列表失败';
      setError(msg);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchProjects(); }, [fetchProjects]);

  const resetForm = () => {
    setName(''); setGenre(''); setDesc(''); setTargetReader('');
    setTotalGoal(100000); setDailyGoal(3000);
  };

  const handleCreate = async () => {
    if (!name.trim() || !genre.trim()) {
      toast.error('请填写项目名称和题材', 4000);
      return;
    }
    setSubmitting(true);
    try {
      await api.post('/projects/', {
        name: name.trim(),
        description: desc.trim() || undefined,
        genre: genre.trim(),
        target_reader: targetReader.trim() || undefined,
        total_word_goal: Number(totalGoal) || 100000,
        daily_word_goal: Number(dailyGoal) || 3000,
        chapter_word_goal: 3000,
      });
      toast.success('项目已创建');
      setShowCreate(false);
      resetForm();
      fetchProjects();
    } catch (err) {
      const msg = err?.response?.data?.detail || err.message || '创建失败';
      toast.error(msg, 6000);
    } finally { setSubmitting(false); }
  };

  const handleStart = async (id) => {
    try {
      await api.post(`/projects/${id}/start`);
      toast.success('项目已启动');
      fetchProjects();
    } catch (err) { toast.error(err?.response?.data?.detail || '启动失败', 5000); }
  };

  const handlePause = async (id) => {
    try {
      await api.post(`/projects/${id}/pause`);
      toast.success('项目已暂停');
      fetchProjects();
    } catch (err) { toast.error(err?.response?.data?.detail || '暂停失败', 5000); }
  };

  const handleDelete = async (id, name) => {
    const ok = await confirm({ title: '删除项目', message: `确定要删除项目「${name || id}」吗？此操作不可撤销，所有相关数据将被删除。` });
    if (!ok) return;
    try {
      await api.del(`/projects/${id}`);
      toast.success('项目已删除');
      fetchProjects();
    } catch (err) { toast.error(err?.response?.data?.detail || '删除失败', 6000); }
  };

  return (
    <div className={styles.page}>
      <PageHeader
        title={PAGE_TITLE}
        subtitle={PAGE_SUBTITLE}
        actions={
          <Button variant="primary" size="sm" onClick={() => { resetForm(); setShowCreate(true); }}>
            + 新建项目
          </Button>
        }
      />

      <AsyncState loading={loading} error={error} onRetry={fetchProjects} isEmpty={projects.length === 0} emptyTitle="暂无项目"
        emptyHint="创建第一个小说项目开始">
        <SectionCard title="项目列表" subtitle={`共 ${projects.length} 个项目`}>
          <div className={styles.grid}>
            {projects.map((p) => {
              const st = STATUS_MAP[p.status] || STATUS_MAP.draft;
              return (
                <div key={p.id} className={styles.card}>
                  <div className={styles.cardTop}>
                    <Link to={`/projects/${p.id}`} className={styles.cardTitle}>{p.name}</Link>
                    <Badge variant={st.variant}>{st.label}</Badge>
                  </div>
                  <div className={styles.cardBody}>
                    <div className={styles.metaRow}><span className={styles.metaLabel}>题材</span><span>{p.genre || '-'}</span></div>
                    <div className={styles.metaRow}><span className={styles.metaLabel}>当前章节</span><span>第 {p.current_chapter_index} 章</span></div>
                    <div className={styles.metaRow}><span className={styles.metaLabel}>已写字数</span><span>{(p.total_words_written || 0).toLocaleString()}</span></div>
                    <div className={styles.metaRow}><span className={styles.metaLabel}>创建时间</span><span>{p.created_at ? new Date(p.created_at).toLocaleDateString() : '-'}</span></div>
                  </div>
                  <div className={styles.cardActions}>
                    <Link to={`/projects/${p.id}`}><Button variant="secondary" size="sm">进入详情</Button></Link>
                    {p.status === 'draft' || p.status === 'paused' ? (
                      <Button variant="primary" size="sm" onClick={() => handleStart(p.id)}>启动</Button>
                    ) : (
                      <Button variant="secondary" size="sm" onClick={() => handlePause(p.id)}>暂停</Button>
                    )}
                    <Button variant="danger" size="sm" onClick={() => handleDelete(p.id, p.name)}>删除</Button>
                  </div>
                </div>
              );
            })}
          </div>
        </SectionCard>
      </AsyncState>

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="新建项目" size="md" footer={
        <div className={styles.modalActions}>
          <Button variant="primary" onClick={handleCreate} disabled={submitting}>{submitting ? '创建中…' : '创建'}</Button>
          <Button variant="secondary" onClick={() => { setShowCreate(false); resetForm(); }}>取消</Button>
        </div>
      }>
        <div className={styles.formGrid}>
          <label className={styles.fullWidth}>
            <span>项目名称 *</span>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="我的小说项目" />
          </label>
          <label className={styles.fullWidth}>
            <span>题材 *</span>
            <input value={genre} onChange={(e) => setGenre(e.target.value)} placeholder="玄幻 / 都市 / 科幻 ..." />
          </label>
          <label className={styles.fullWidth}>
            <span>简介</span>
            <textarea value={desc} onChange={(e) => setDesc(e.target.value)} rows={3} placeholder="项目背景、目标读者..." />
          </label>
          <label>
            <span>目标读者</span>
            <input value={targetReader} onChange={(e) => setTargetReader(e.target.value)} placeholder="如：18-30岁 男性" />
          </label>
          <label>
            <span>总字数目标</span>
            <input type="number" value={totalGoal} onChange={(e) => setTotalGoal(e.target.value)} />
          </label>
          <label>
            <span>每日字数目标</span>
            <input type="number" value={dailyGoal} onChange={(e) => setDailyGoal(e.target.value)} />
          </label>
        </div>
      </Modal>

      <ConfirmModal state={confirmState} onOk={handleOk} onCancel={handleCancel} />
    </div>
  );
}

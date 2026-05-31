import React, { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import api from '../services/api';
import { useToast } from '../contexts/ToastContext';
import { useConfirm } from '../hooks/useConfirm';
import { Icon } from '../components/ui/Icon';
import { AsyncState } from '../components/ui/AsyncState';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { StatCard } from '../components/ui/StatCard';
import ConfirmModal from '../components/ConfirmModal';
import Modal from '../components/ui/Modal';
import styles from './ProjectDetail.module.css';

const PAGE_TITLE = '项目详情';
const PAGE_ICON = 'FileText';

const STATUS_MAP = {
  draft: { label: '草稿', variant: 'muted' },
  active: { label: '进行中', variant: 'success' },
  paused: { label: '已暂停', variant: 'warning' },
  completed: { label: '已完成', variant: 'accent' },
};

export default function ProjectDetail() {
  const { id } = useParams();
  const projectId = Number(id);
  const toast = useToast();
  const { confirm, state: confirmState, handleOk, handleCancel } = useConfirm();

  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [playbook, setPlaybook] = useState(null);
  const [failures, setFailures] = useState([]);
  const [showPlaybook, setShowPlaybook] = useState(false);
  const [savingPlaybook, setSavingPlaybook] = useState(false);

  const fetchAll = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    setError('');
    try {
      const [pRes, pbRes, fRes] = await Promise.all([
        api.get(`/projects/${projectId}`),
        api.get(`/projects/${projectId}/playbook`).catch(() => ({ data: null })),
        api.get(`/projects/${projectId}/failures`).catch(() => ({ data: [] })),
      ]);
      setProject(pRes.data);
      setPlaybook(pbRes.data);
      setFailures(toArray(fRes.data));
    } catch (err) {
      const msg = err?.response?.data?.detail || err.message || '加载项目详情失败';
      setError(msg);
    } finally { setLoading(false); }
  }, [projectId]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const [playbookRules, setPlaybookRules] = useState([]);
  const [playbookStyle, setPlaybookStyle] = useState('');
  const [playbookTone, setPlaybookTone] = useState('');

  useEffect(() => {
    if (playbook) {
      setPlaybookRules(toArray(playbook?.rules));
      setPlaybookStyle(playbook.style_boundaries || '');
      setPlaybookTone(playbook.tone_guidelines || '');
    }
  }, [playbook]);

  const handleSavePlaybook = async () => {
    setSavingPlaybook(true);
    try {
      await api.post(`/projects/${projectId}/playbook`, {
        rules: playbookRules,
        style_boundaries: playbookStyle,
        tone_guidelines: playbookTone,
      });
      toast.success('Playbook 已保存');
      setShowPlaybook(false);
      fetchAll();
    } catch (err) {
      toast.error(err?.response?.data?.detail || '保存失败', 5000);
    } finally { setSavingPlaybook(false); }
  };

  const handleDeleteProject = async () => {
    const ok = await confirm({ title: '删除项目', message: `确定要删除项目「${project?.name || ''}」？此操作不可撤销。` });
    if (!ok) return;
    try {
      await api.del(`/projects/${projectId}`);
      toast.success('项目已删除');
      window.location.href = '/projects';
    } catch (err) { toast.error(err?.response?.data?.detail || '删除失败', 6000); }
  };

  if (!projectId) return (
    <div className={styles.page}><p className={styles.err}>无效的项目 ID</p></div>
  );

  const st = project ? STATUS_MAP[project.status] || STATUS_MAP.draft : STATUS_MAP.draft;
  const goals = project?.goals || {};
  const quality = project?.quality || {};
  const progress = project?.progress || {};
  const bible = project?.bible || null;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <Link to="/projects" className={styles.back}>← 返回项目列表</Link>
        <h1 className={styles.title}><Icon name={PAGE_ICON} size={22} /><span>{project?.name || PAGE_TITLE}</span>
          <Badge variant={st.variant} className={styles.headerBadge}>{st.label}</Badge>
        </h1>
        <div className={styles.summary}>
          <span>题材：{project?.genre || '-'}</span>
          <span>当前：第 {progress.current_chapter || 0} 章</span>
          <span>已写：{(progress.total_words || 0).toLocaleString()} 字</span>
        </div>
      </header>

      {error && !project && <p className={styles.err}>{error}</p>}

      {project && (
        <>
          {/* Stats */}
          <div className={styles.statsGrid}>
            <StatCard label="当前章节" value={progress.current_chapter || 0} />
            <StatCard label="已写字数" value={(progress.total_words || 0).toLocaleString()} unit="字" />
            <StatCard label="总目标" value={(goals.total_word || 0).toLocaleString()} unit="字" />
            <StatCard label="日目标" value={goals.daily_word || 0} unit="字/日" />
          </div>

          {/* Bible Summary */}
          {bible && (
            <section className={styles.card}>
              <h2 className={styles.cardTitle}>📖 世界观摘要</h2>
              <p className={styles.bibleText}>{bible.world_setting || '暂无设定'}</p>
              {toArray(bible?.characters).length > 0 && (
                <div className={styles.charChips}>
                  {bible.characters.slice(0, 12).map((c, i) => (
                    <span key={i} className={styles.charChip}>{typeof c === 'string' ? c : c?.name || JSON.stringify(c)}</span>
                  ))}
                </div>
              )}
            </section>
          )}

          {/* Actions */}
          <section className={styles.card}>
            <h2 className={styles.cardTitle}>🚀 快捷操作</h2>
            <div className={styles.actionGrid}>
              <Link to={`/bible-editor?project_id=${projectId}`}><Button variant="primary">编辑世界观</Button></Link>
              <Link to="/factory"><Button variant="secondary">进入写作工厂</Button></Link>
              <Link to="/tasks"><Button variant="secondary">任务队列</Button></Link>
              <Link to="?view=feedback"><Button variant="secondary">反馈中心</Button></Link>
              {project.status !== 'active' ? (
                <Button variant="primary" onClick={async () => { try { await api.post(`/projects/${projectId}/start`); toast.success('项目已启动'); fetchAll(); } catch (e) { toast.error(e?.response?.data?.detail || '启动失败'); } }}>启动项目</Button>
              ) : (
                <Button variant="secondary" onClick={async () => { try { await api.post(`/projects/${projectId}/pause`); toast.success('项目已暂停'); fetchAll(); } catch (e) { toast.error(e?.response?.data?.detail || '暂停失败'); } }}>暂停项目</Button>
              )}
              <Button variant="danger" onClick={handleDeleteProject}>删除项目</Button>
            </div>
          </section>

          {/* Playbook */}
          <section className={styles.card}>
            <div className={styles.cardHeader}>
              <h2 className={styles.cardTitle}>📝 写作手册（Playbook）</h2>
              <Button variant="secondary" size="sm" onClick={() => { if (playbook) { setPlaybookRules(toArray(playbook?.rules)); setPlaybookStyle(playbook.style_boundaries || ''); setPlaybookTone(playbook.tone_guidelines || ''); } setShowPlaybook(true); }}>编辑</Button>
            </div>
            {playbook ? (
              <div className={styles.playbookBody}>
                <p><strong>规则数：</strong>{playbook.rules_count || playbook.rules?.length || 0} 条</p>
                <p><strong>风格边界：</strong>{playbook.style_boundaries || '未设置'}</p>
                <p><strong>语气指南：</strong>{playbook.tone_guidelines || '未设置'}</p>
              </div>
            ) : <p className={styles.empty}>暂无 Playbook，点击"编辑"创建。</p>}
          </section>

          {/* Failures */}
          <section className={styles.card}>
            <h2 className={styles.cardTitle}>⚠️ 失败模式记录</h2>
            <AsyncState loading={false} error={null} isEmpty={failures.length === 0} emptyTitle="暂无失败记录，继续保持！" hideLoading hideError>
              <div className={styles.failureList}>
                {failures.map((f) => (
                  <div key={f.id} className={styles.failureItem}>
                    <div className={styles.failureHead}>
                      <Badge variant="danger">{f.category}</Badge>
                      <span className={styles.failureCount}>×{f.occurrence_count || 1}</span>
                    </div>
                    <p className={styles.failureSymptom}>{f.symptom}</p>
                    <p className={styles.failurePrevention}><strong>预防：</strong>{f.prevention_rule}</p>
                  </div>
                ))}
              </div>
            </AsyncState>
          </section>
        </>
      )}

      {/* Playbook Edit Modal */}
      <Modal open={showPlaybook} onClose={() => setShowPlaybook(false)} title="编辑 Playbook" size="lg" footer={
        <div className={styles.modalActions}>
          <Button variant="primary" onClick={handleSavePlaybook} disabled={savingPlaybook}>{savingPlaybook ? '保存中…' : '保存'}</Button>
          <Button variant="secondary" onClick={() => setShowPlaybook(false)}>取消</Button>
        </div>
      }>
        <div className={styles.formGrid}>
          <label className={styles.fullWidth}>
            <span>写作规则（每行一条）</span>
            <textarea value={playbookRules.join('\n')} onChange={(e) => setPlaybookRules(e.target.value.split('\n').filter(Boolean))} rows={8} placeholder="每行一条规则..." />
          </label>
          <label className={styles.fullWidth}>
            <span>风格边界</span>
            <textarea value={playbookStyle} onChange={(e) => setPlaybookStyle(e.target.value)} rows={4} placeholder="不能做的写作方式..." />
          </label>
          <label className={styles.fullWidth}>
            <span>语气指南</span>
            <textarea value={playbookTone} onChange={(e) => setPlaybookTone(e.target.value)} rows={4} placeholder="叙事语气、对话风格..." />
          </label>
        </div>
      </Modal>

      <ConfirmModal state={confirmState} onOk={handleOk} onCancel={handleCancel} />
    </div>
  );
}

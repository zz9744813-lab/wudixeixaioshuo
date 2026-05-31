import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import { useToast } from '../contexts/ToastContext';
import { useConfirm } from '../hooks/useConfirm';
import { Icon } from '../components/ui/Icon';
import { AsyncState } from '../components/ui/AsyncState';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import ConfirmModal from '../components/ConfirmModal';
import Modal from '../components/ui/Modal';
import { toObject, toArray } from '../utils/nullSafety';
import styles from './WritingFactory.module.css';

const PAGE_TITLE = '24小时写作工厂';
const PAGE_ICON = 'Factory';

export default function WritingFactory() {
  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [plan, setPlan] = useState(null);
  const [queue, setQueue] = useState(null);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [loadingPlan, setLoadingPlan] = useState(false);
  const [loadingQueue, setLoadingQueue] = useState(false);
  const [showPlanModal, setShowPlanModal] = useState(false);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  const toast = useToast();
  const { confirm, state: confirmState, handleOk, handleCancel } = useConfirm();

  const fetchProjects = useCallback(async () => {
    setLoadingProjects(true);
    try {
      const res = await api.get('/projects/');
      setProjects(toArray(res.data));
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || '加载项目失败');
    } finally { setLoadingProjects(false); }
  }, []);

  const fetchPlan = useCallback(async () => {
    if (!selectedProjectId) return;
    setLoadingPlan(true);
    setError('');
    try {
      const res = await api.get(`/worker/plan/${selectedProjectId}`);
      setPlan(res.data || {});
    } catch (err) {
      setPlan({});
      setError(err?.response?.data?.detail || err.message || '加载计划失败');
    } finally { setLoadingPlan(false); }
  }, [selectedProjectId]);

  const fetchQueue = useCallback(async () => {
    setLoadingQueue(true);
    try {
      const res = await api.get('/worker/queue/status');
      setQueue(res.data || {});
    } catch (err) {
      setQueue({});
    } finally { setLoadingQueue(false); }
  }, []);

  useEffect(() => { fetchProjects(); }, [fetchProjects]);
  useEffect(() => { if (selectedProjectId) { fetchPlan(); fetchQueue(); } }, [selectedProjectId, fetchPlan, fetchQueue]);

  const handleAddToQueue = async () => {
    if (!selectedProjectId) { toast.error('请先选择项目', 4000); return; }
    setActionLoading(true);
    try {
      const res = await api.post('/worker/queue/add', { project_id: Number(selectedProjectId) });
      toast.success(res.data?.message || '已添加到队列');
      fetchQueue();
      fetchPlan();
    } catch (err) { toast.error(err?.response?.data?.detail || err.message || '添加失败', 6000); }
    finally { setActionLoading(false); }
  };

  const handleRemoveFromQueue = async (chapterId) => {
    try {
      await api.del(`/worker/queue/${chapterId}`);
      toast.success('已从队列移除');
      fetchQueue();
      fetchPlan();
    } catch { toast.error('移除失败', 5000); }
  };

  const handleClearQueue = async () => {
    const ok = await confirm({ title: '清空队列', message: '确定要清空整个写作队列吗？' });
    if (!ok) return;
    try {
      await api.post('/worker/queue/clear-failed');
      toast.success('队列已清空');
      fetchQueue();
      fetchPlan();
    } catch { toast.error('清空失败', 5000); }
  };

  const planObj = toObject(plan);
  const queueObj = toObject(queue);
  const planChapters = toArray(planObj?.chapters);
  const queueTasks = toArray(queueObj?.tasks);

  const handleViewPlan = () => setShowPlanModal(true);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}><Icon name={PAGE_ICON} size={22} /><span>{PAGE_TITLE}</span></h1>
      </header>

      <AsyncState loading={loadingProjects} error={error} onRetry={fetchProjects} emptyTitle="暂无项目" emptyHint="请先创建项目">
        <div className={styles.selectorRow}>
          <span className={styles.label}>选择项目：</span>
          <select className={styles.select} value={selectedProjectId} onChange={(e) => setSelectedProjectId(e.target.value)}>
            <option value="">-- 请选择 --</option>
            {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <Button variant="primary" size="sm" onClick={handleAddToQueue} disabled={!selectedProjectId || actionLoading}>
            {actionLoading ? '操作中…' : '+ 加入队列'}
          </Button>
          <Button variant="ghost" size="sm" onClick={handleClearQueue}>清空队列</Button>
        </div>
      </AsyncState>

      <div className={styles.sections}>
        {/* Plan Preview */}
        <section className={styles.card}>
          <div className={styles.cardHeader}>
            <h2 className={styles.cardTitle}>写作计划预览</h2>
            <Button variant="ghost" size="sm" onClick={handleViewPlan} disabled={!selectedProjectId}>查看完整计划</Button>
          </div>
          <AsyncState loading={loadingPlan} error={null} isEmpty={!planChapters.length} emptyTitle="计划为空" hideLoading hideError>
            <div className={styles.chapterList}>
              {planChapters.slice(0, 10).map((ch, idx) => (
                <div key={ch.id || idx} className={styles.chapterItem}>
                  <span className={styles.chapterIdx}>#{idx + 1}</span>
                  <span className={styles.chapterTitle}>{ch.title || `第 ${ch.chapter_index || '?'} 章`}</span>
                  <Badge variant={ch.status === 'completed' ? 'success' : ch.status === 'writing' ? 'warning' : 'accent'}>
                    {ch.status || '待处理'}
                  </Badge>
                </div>
              ))}
              {planChapters.length > 10 && (
                <p className={styles.moreHint}>还有 {planChapters.length - 10} 章未显示，点击「查看完整计划」</p>
              )}
            </div>
          </AsyncState>
        </section>

        {/* Queue */}
        <section className={styles.card}>
          <h2 className={styles.cardTitle}>当前队列 ({queueTasks.length})</h2>
          <AsyncState loading={loadingQueue} error={null} isEmpty={!queueTasks.length} emptyTitle="队列为空" hideLoading hideError>
            <div className={styles.chapterList}>
              {queueTasks.map((item, idx) => (
                <div key={item.id || item.chapter_id || idx} className={styles.chapterItem}>
                  <span className={styles.chapterIdx}>#{idx + 1}</span>
                  <span>{item.project_name || `项目 ${item.project_id}`}</span>
                  <span className={styles.chapterTitle}>第 {item.chapter_index || item.chapter_id} 章</span>
                  <Badge variant={item.status === 'completed' ? 'success' : item.status === 'failed' ? 'danger' : item.status === 'running' ? 'warning' : 'accent'}>
                    {item.status || 'pending'}
                  </Badge>
                </div>
              ))}
            </div>
          </AsyncState>
        </section>

        {/* 快捷导航 */}
        <section className={styles.card}>
          <h2 className={styles.cardTitle}>快捷操作</h2>
          <div className={styles.actionGrid}>
            <Link to="/projects" className={styles.actionCard}>
              <Icon name="FolderOpen" size={20} /><span>项目管理</span>
            </Link>
            <Link to="/tasks" className={styles.actionCard}>
              <Icon name="ListChecks" size={20} /><span>任务队列</span>
            </Link>
            <Link to="/worker" className={styles.actionCard}>
              <Icon name="Bot" size={20} /><span>Worker 控制台</span>
            </Link>
            <Link to="/usage" className={styles.actionCard}>
              <Icon name="Activity" size={20} /><span>用量统计</span>
            </Link>
          </div>
        </section>
      </div>

      <Modal open={showPlanModal} onClose={() => setShowPlanModal(false)} title="写作计划详情" size="md">
        {!planChapters.length ? (
          <p style={{ color: 'var(--text-muted)' }}>计划为空</p>
        ) : (
          <div className={styles.fullPlanList}>
            {planChapters.map((ch, idx) => (
              <div key={ch.id || idx} className={styles.planItem}>
                <strong>第 {ch.chapter_index || idx + 1} 章：{ch.title || '未命名'}</strong>
                <span> — {ch.status || '待处理'}</span>
              </div>
            ))}
          </div>
        )}
      </Modal>

      <ConfirmModal state={confirmState} onOk={handleOk} onCancel={handleCancel} />
    </div>
  );
}

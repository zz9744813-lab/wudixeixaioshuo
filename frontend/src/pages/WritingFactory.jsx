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
import styles from './WritingFactory.module.css';

const PAGE_TITLE = '🏭 24小时写作工厂';
const PAGE_ICON = 'Factory';

export default function WritingFactory() {
  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [plan, setPlan] = useState(null);
  const [queue, setQueue] = useState(null);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [loadingPlan, setLoadingPlan] = useState(false);
  const [loadingQueue, setLoadingQueue] = useState(false);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  const toast = useToast();
  const { confirm, state: confirmState, handleOk, handleCancel } = useConfirm();

  const fetchProjects = useCallback(async () => {
    setLoadingProjects(true);
    try {
      const res = await api.get('/projects/');
      setProjects(Array.isArray(res.data) ? res.data : []);
      if (res.data?.length && !selectedProjectId) {
        setSelectedProjectId(String(res.data[0].id));
      }
    } catch (err) { setError(err?.response?.data?.detail || '加载项目失败'); }
    finally { setLoadingProjects(false); }
  }, []);

  useEffect(() => { fetchProjects(); }, [fetchProjects]);

  const fetchPlan = useCallback(async () => {
    if (!selectedProjectId) return;
    setLoadingPlan(true);
    try {
      const res = await api.get(`/worker/plan/${selectedProjectId}`);
      setPlan(res.data);
    } catch (err) { setPlan(null); }
    finally { setLoadingPlan(false); }
  }, [selectedProjectId]);

  const fetchQueue = useCallback(async () => {
    setLoadingQueue(true);
    try {
      const res = await api.get('/worker/queue/status');
      setQueue(res.data);
    } catch (err) { setQueue(null); }
    finally { setLoadingQueue(false); }
  }, []);

  useEffect(() => { if (selectedProjectId) fetchPlan(); }, [selectedProjectId, fetchPlan]);
  useEffect(() => { fetchQueue(); }, [fetchQueue]);

  const handleAddToQueue = async () => {
    if (!selectedProjectId) { toast.error('请先选择项目', 4000); return; }
    setActionLoading(true);
    try {
      const res = await api.post('/worker/queue/add', { project_id: Number(selectedProjectId) });
      toast.success(res.data?.message || '已添加到队列');
      fetchQueue();
      fetchPlan();
    } catch (err) { toast.error(err?.response?.data?.detail || '添加失败', 6000); }
    finally { setActionLoading(false); }
  };

  const handleRemoveFromQueue = async (chapterId) => {
    try {
      await api.del(`/worker/queue/${chapterId}`);
      toast.success('已从队列移除');
      fetchQueue();
      fetchPlan();
    } catch (err) { toast.error(err?.response?.data?.detail || '移除失败', 5000); }
  };

  const handleReorder = async (taskIds) => {
    try {
      await api.post('/worker/queue/reorder', { task_ids: taskIds });
      toast.success('队列已重新排序');
      fetchQueue();
    } catch (err) { toast.error(err?.response?.data?.detail || '排序失败', 5000); }
  };

  const startWorker = async () => {
    const ok = await confirm({ title: '启动 Worker', message: '确定要启动 24 小时自动写作吗？' });
    if (!ok) return;
    setActionLoading(true);
    try {
      const res = await api.post('/worker/control', { action: 'start' });
      toast.success(res.data?.message || 'Worker 已启动');
      // Briefly refresh status
      setTimeout(() => window.location.reload(), 1500);
    } catch (err) { toast.error(err?.response?.data?.detail || '启动失败', 6000); }
    finally { setActionLoading(false); }
  };

  const selectedProject = projects.find((p) => String(p.id) === selectedProjectId);
  const queueTasks = Array.isArray(queue?.tasks) ? queue.tasks : [];
  const planChapters = Array.isArray(plan?.chapters) ? plan.chapters : [];

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}><Icon name={PAGE_ICON} size={22} /><span>{PAGE_TITLE}</span></h1>
        <div className={styles.headerActions}>
          <select className={styles.projectSelect} value={selectedProjectId} onChange={(e) => setSelectedProjectId(e.target.value)}>
            <option value="">-- 选择项目 --</option>
            {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <Button variant="primary" onClick={handleAddToQueue} disabled={!selectedProjectId || actionLoading}>
            {actionLoading ? '添加中…' : '+ 添加章节到队列'}
          </Button>
          <Link to="/worker"><Button variant="secondary">Worker 控制台</Button></Link>
        </div>
      </header>

      {selectedProject && (
        <p className={styles.currentProject}>当前项目：<strong>{selectedProject.name}</strong> · {selectedProject.genre || '未知题材'} · 第 {selectedProject.current_chapter_index || 0} 章</p>
      )}

      <div className={styles.grid}>
        {/* Writing Plan */}
        <section className={styles.card}>
          <div className={styles.cardHeader}>
            <h2 className={styles.cardTitle}>📝 写作计划</h2>
            <Button variant="ghost" size="sm" onClick={fetchPlan} disabled={loadingPlan}>刷新</Button>
          </div>
          <AsyncState loading={loadingPlan} error={null} isEmpty={!planChapters.length} emptyTitle="暂无计划，请先添加章节到队列" hideLoading hideError>
            <div className={styles.planList}>
              {planChapters.map((ch, idx) => (
                <div key={ch.id || ch.chapter_index || idx} className={styles.planItem}>
                  <span className={styles.planIdx}>#{idx + 1}</span>
                  <span className={styles.planTitle}>{ch.title || `第 ${ch.chapter_index || idx + 1} 章`}</span>
                  <span className={styles.planWords}>{(ch.word_goal || ch.word_count || 3000)} 字</span>
                  <Badge variant={ch.status === 'completed' ? 'success' : ch.status === 'writing' ? 'warning' : 'accent'}>{ch.status || 'pending'}</Badge>
                </div>
              ))}
            </div>
          </AsyncState>
        </section>

        {/* Queue */}
        <section className={styles.card}>
          <div className={styles.cardHeader}>
            <h2 className={styles.cardTitle}>📋 写作队列 ({queueTasks.length})</h2>
            <Button variant="ghost" size="sm" onClick={fetchQueue} disabled={loadingQueue}>刷新</Button>
          </div>
          <AsyncState loading={loadingQueue} error={null} isEmpty={queueTasks.length === 0} emptyTitle="队列为空" hideLoading hideError>
            <div className={styles.queueList}>
              {queueTasks.map((item, idx) => (
                <div key={item.id || item.chapter_id || idx} className={styles.queueItem}>
                  <span className={styles.queueIdx}>#{idx + 1}</span>
                  <span className={styles.queueName}>{item.project_name || `项目 ${item.project_id}`}</span>
                  <span className={styles.queueChapter}>第 {item.chapter_index || item.chapter_id} 章</span>
                  <Badge variant={item.status === 'completed' ? 'success' : item.status === 'failed' ? 'danger' : item.status === 'running' ? 'warning' : 'accent'}>{item.status || 'pending'}</Badge>
                  <div className={styles.queueActions}>
                    {idx > 0 && <Button variant="ghost" size="sm" onClick={() => {
                      const newOrder = [queueTasks[idx - 1].id || queueTasks[idx - 1].chapter_id, item.id || item.chapter_id];
                      handleReorder(newOrder);
                    }}>↑</Button>}
                    {idx < queueTasks.length - 1 && <Button variant="ghost" size="sm" onClick={() => {
                      const newOrder = [item.id || item.chapter_id, queueTasks[idx + 1].id || queueTasks[idx + 1].chapter_id];
                      handleReorder(newOrder);
                    }}>↓</Button>}
                    <Button variant="danger" size="sm" onClick={() => handleRemoveFromQueue(item.chapter_id || item.id)}>移除</Button>
                  </div>
                </div>
              ))}
            </div>
          </AsyncState>
          {queueTasks.length > 0 && (
            <div className={styles.queueFooter}>
              <Button variant="primary" onClick={startWorker} disabled={actionLoading}>
                {actionLoading ? '启动中…' : '▶ 启动 Worker 开始写作'}
              </Button>
              <Link to="/tasks"><Button variant="secondary">查看任务</Button></Link>
            </div>
          )}
        </section>
      </div>

      <ConfirmModal state={confirmState} onOk={handleOk} onCancel={handleCancel} />
    </div>
  );
}

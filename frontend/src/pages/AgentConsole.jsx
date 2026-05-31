import React, { useState, useEffect, useCallback } from 'react';
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
import styles from './AgentConsole.module.css';

const PAGE_TITLE = '🤖 Agent 控制台';
const PAGE_ICON = 'Bot';

const AGENT_STATUS_COLORS = {
  ready: 'success',
  running: 'warning',
  idle: 'accent',
  error: 'danger',
};

const STATUS_TEXTS = {
  pending: '等待中',
  running: '运行中',
  completed: '已完成',
  failed: '失败',
};

export default function AgentConsole() {
  const toast = useToast();
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [selectedChapterIndex, setSelectedChapterIndex] = useState(1);
  const [generating, setGenerating] = useState(false);
  const [runDetailId, setRunDetailId] = useState(null);
  const [runDetailData, setRunDetailData] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const { data: statusData, loading, error, reload } = useFetch('/agents/status');
  const { data: projects = [], loading: loadingProjects } = useFetch('/projects/');

  useEffect(() => {
    if (projects.length && !selectedProjectId) {
      setSelectedProjectId(String(projects[0]?.id));
    }
  }, [projects]);

  const fetchRunDetail = useCallback(async (id) => {
    setRunDetailId(id);
    setLoadingDetail(true);
    setRunDetailData(null);
    try {
      const res = await api.get(`/agent-runs/${id}`);
      setRunDetailData(res.data);
    } catch (err) {
      toast.error('加载运行详情失败');
    } finally {
      setLoadingDetail(false);
    }
  }, [toast]);

  const handleGenerate = async () => {
    if (!selectedProjectId) {
      toast.error('请先选择项目');
      return;
    }
    setGenerating(true);
    try {
      const res = await api.post('/agents/generate-chapter', {
        project_id: Number(selectedProjectId),
        chapter_index: selectedChapterIndex,
      });
      toast.success(res.data?.message || '章节生成完成');
      reload();
    } catch (err) {
      toast.error(err?.response?.data?.detail || '生成失败', 6000);
    } finally {
      setGenerating(false);
    }
  };

  const handleStartRun = async () => {
    if (!selectedProjectId) {
      toast.error('请先选择项目');
      return;
    }
    setGenerating(true);
    try {
      const res = await api.post('/agent-runs', {
        project_id: Number(selectedProjectId),
        mode: 'autonomous',
        user_request: `生成项目第 ${selectedChapterIndex} 章`,
      });
      toast.success(res.data?.message || '运行已创建');
      reload();
    } catch (err) {
      toast.error(err?.response?.data?.detail || '启动失败', 6000);
    } finally {
      setGenerating(false);
    }
  };

  const selectedProject = projects.find((p) => String(p.id) === selectedProjectId);

  const agentList = statusData?.agents || [];
  const columns = [
    { key: 'name', label: 'Agent', render: (v, row) => <Badge variant={AGENT_STATUS_COLORS[row.status] || 'accent'}>{v}</Badge> },
    { key: 'description', label: '职责' },
    { key: 'status', label: '状态', render: (v) => <Badge variant={AGENT_STATUS_COLORS[v] || 'accent'}>{v}</Badge> },
  ];

  const stats = [
    { label: 'Run 状态', value: statusData?.status || 'idle' || '?', hint: 'running tasks: ' + (statusData?.running_tasks || 0) },
    { label: 'LLM 状态', value: statusData?.llm_status || 'unknown' || '?', unit: '', hint: statusData?.llm_provider || '' },
    { label: '待处理', value: statusData?.pending_tasks ?? 0, unit: 'tasks' },
  ];

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}><Icon name={PAGE_ICON} size={22} /><span>{PAGE_TITLE}</span></h1>
      </header>

      <div className={styles.statsRow}>
        {stats.map((s) => <StatCard key={s.label} {...s} />)}
      </div>

      <div className={styles.body}>
        <AsyncState loading={loading} error={error} onRetry={reload}>
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Agent 列表</h2>
            <Table columns={columns} rows={agentList} rowKey="name" />
          </section>

          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>章节生成</h2>
            <div className={styles.formRow}>
              <select
                className={styles.select}
                value={selectedProjectId}
                onChange={(e) => setSelectedProjectId(e.target.value)}
                disabled={loadingProjects}
              >
                <option value="">-- 选择项目 --</option>
                {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
              <input
                type="number"
                className={styles.input}
                value={selectedChapterIndex}
                onChange={(e) => setSelectedChapterIndex(Number(e.target.value))}
                min={1}
              />
              <Button variant="primary" onClick={handleGenerate} loading={generating}>生成章节</Button>
            </div>
            {selectedProject && <p className={styles.hint}>当前项目：{selectedProject.name} · 题材：{selectedProject.genre || '-'}</p>}
          </section>
        </AsyncState>
      </div>

      <Modal open={!!runDetailId} onClose={() => setRunDetailId(null)} title={runDetailData?.user_request || '运行详情'}>
        {loadingDetail ? (
          <div className={styles.detailSkeleton} />
        ) : runDetailData ? (
          <div className={styles.detailBody}>
            <div className={styles.detailMeta}>
              <Badge variant={AGENT_STATUS_COLORS[runDetailData.status] || 'accent'}>{STATUS_TEXTS[runDetailData.status] || runDetailData.status}</Badge>
              <span>模式：{runDetailData.mode}</span>
            </div>
            {runDetailData.steps && (
              <Table
                columns={[
                  { key: 'agent', label: 'Agent' },
                  { key: 'status', label: '状态', render: (v) => <Badge variant={v === 'completed' ? 'success' : v === 'running' ? 'warning' : 'accent'}>{v}</Badge> },
                  { key: 'tokens', label: 'Tokens', align: 'right' },
                  { key: 'score', label: '评分', align: 'right', render: (v) => v ? `${v} 分` : '-' },
                ]}
                rows={runDetailData.steps}
                rowKey="agent"
              />
            )}
          </div>
        ) : null}
      </Modal>
    </div>
  );
}

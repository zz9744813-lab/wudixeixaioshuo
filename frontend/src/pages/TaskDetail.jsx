import React, { useState, useCallback, useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import api from '../services/api';
import { useToast } from '../contexts/ToastContext';
import ConfirmModal from '../components/ConfirmModal';
import { useConfirm } from '../hooks/useConfirm';
import styles from './TaskDetail.module.css';

const AGENT_LABELS = {
  Planner: '规划',
  Draft: '起草',
  ParallelDraft: '并行起草',
  Critic: '审稿',
  ParallelCritic: '并行审稿',
  Rewrite: '改稿',
  Continuity: '连续性',
  Learning: '复盘',
};

function MetaBlock({ title, children }) {
  if (!children) return null;
  return (
    <div className={styles.metaBlock}>
      <div className={styles.metaTitle}>{title}</div>
      <div className={styles.metaBody}>{children}</div>
    </div>
  );
}

function StepCard({ step }) {
  const [stepOpen, setStepOpen] = useState(false);
  const meta = step.context_metadata || {};
  const dims = step.score_breakdown || {};

  return (
    <div className={styles.stepCard}>
      <button type="button" className={styles.stepHead} onClick={() => setStepOpen((v) => !v)}>
        <span className={styles.stepName}>
          #{step.step_index} {AGENT_LABELS[step.agent_name] || step.agent_name}
        </span>
        <span className={styles.stepMetaInline}>
          {step.score != null && <em className={styles.score}>评分 {step.score}</em>}
          {step.model_name && step.model_name !== 'unknown' && (<em className={styles.model}>{step.model_name}</em>)}
          <span>{stepOpen ? '收起' : '展开'}</span>
        </span>
      </button>

      {stepOpen && (
        <div className={styles.stepBody}>
          <MetaBlock title="模型 / 成本 / 耗时">
            <span>{step.provider_name || '-'} · {step.model_name || '-'}</span>
            <span>tokens {step.input_tokens || 0}/{step.output_tokens || 0}</span>
            <span>{step.duration_seconds || 0}s</span>
          </MetaBlock>

          {Object.keys(dims).length > 0 && (
            <MetaBlock title="商业 Critic 维度分数">
              <div className={styles.dims}>
                {Object.entries(dims).map(([k, v]) => (<span key={k} className={styles.dim}>{k}: {v}</span>))}
              </div>
            </MetaBlock>
          )}

          <MetaBlock title="并行候选 / 选择理由">
            <ul className={styles.list}>
              {meta.parallel_candidates.map((c) => (
                <li key={c.candidate_id} className={c.candidate_id === meta.selected_candidate_id ? styles.selected : ''}>
                  {c.candidate_id} · {c.strategy} · {c.score} {c.candidate_id === meta.selected_candidate_id && ' ✓'}
                </li>
              ))}
            </ul>
            {meta.selection_reason && <p className={styles.reason}>{meta.selection_reason}</p>}
          </MetaBlock>

          <MetaBlock title="并行 Critic 来源">{meta.critic_sources.join('、')}</MetaBlock>
          <MetaBlock title="召回的记忆">
            <ul className={styles.list}>
              {meta.memory_items.map((m, i) => (<li key={i}>[{m.type}] #{m.id} · 相关度 {m.score}</li>))}
            </ul>
          </MetaBlock>

          {meta.reader_rules_used?.length > 0 && (
            <MetaBlock title="真人训练营规则引用">
              <ul className={styles.list}>
                {meta.reader_rules_used.map((r, i) => (<li key={i}>{typeof r === "string" ? r : JSON.stringify(r)}</li>))}
              </ul>
            </MetaBlock>
          )}

          {step.input_prompt && <MetaBlock title="输入 Prompt"><pre className={styles.pre}>{step.input_prompt}</pre></MetaBlock>}
          {step.raw_output && <MetaBlock title="原始输出"><pre className={styles.pre}>{step.raw_output.slice(0, 4000)}</pre></MetaBlock>}
        </div>
      )}
    </div>
  );
}

export default function TaskDetail() {
  const { id } = useParams();
  const toast = useToast();
  const { confirm, state: confirmState, handleOk, handleCancel } = useConfirm({
    title: '请确认',
    message: '确定要执行此操作吗？',
  });

  const [task, setTask] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [sseTaskId, setSseTaskId] = useState(null);

  useEffect(() => { setSseTaskId(id ? Number(id) : null); }, [id]);

  const fetchTask = useCallback(async () => {
    try {
      const res = await api.get(`/tasks/${id}`);
      setTask(res.data);
      setError('');
    } catch (err) {
      setError(err.response?.data?.detail || err.message || '加载任务详情失败');
    } finally { setLoading(false); }
  }, [id]);

  useEffect(() => { fetchTask(); }, [fetchTask]);

  if (loading) return <div className={styles.page}>加载中...</div>;
  if (error && !task) return <div className={styles.page}><p className={styles.err}>{error}</p></div>;

  return (
    <div className={styles.page}>
      <PageHeader
        title={`任务 #${task?.id}`}
        icon="FileText"
        subtitle={`${task?.task_type} · ${task?.status} · 章节 ${task?.chapter_id}`}
        actions={
          <Link to="/tasks"><Button variant="secondary" size="sm">← 返回任务队列</Button></Link>
        }
      />

      <div className={styles.metricsRow}>
        <MetricCard label="状态" value={task?.status} status="info" />
        <MetricCard label="成本" value={`$${(task?.actual_cost || 0).toFixed(4)}`} status="info" />
        <MetricCard label="耗时" value={`${task?.duration_seconds || 0}s`} status="info" />
      </div>

      <SectionCard title="Agent 执行步骤" subtitle={`共 ${(task?.steps || []).length} 步`}>
        {(task?.steps || []).length === 0 ? (
          <p className={styles.empty}>暂无步骤记录。</p>
        ) : (
          (task?.steps || []).map((step) => <StepCard key={step.id} step={step} />)
        )}
      </SectionCard>

      <ConfirmModal state={confirmState} onOk={handleOk} onCancel={handleCancel} />
    </div>
  );
}

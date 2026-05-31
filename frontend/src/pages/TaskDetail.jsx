import React, { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import api from '../services/api';
import { useToast } from '../contexts/ToastContext';
import ProgressIndicator from '../components/ProgressIndicator';
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
  const [open, setOpen] = useState(false);
  const meta = step.context_metadata || {};
  const dims = step.score_breakdown || {};

  const readerRules = Array.isArray(meta.reader_rules_used)
    ? meta.reader_rules_used
    : typeof meta.reader_rules_used === 'string'
      ? [meta.reader_rules_used]
      : [];

  return (
    <div className={styles.stepCard}>
      <button type="button" className={styles.stepHead} onClick={() => setOpen((v) => !v)}>
        <span className={styles.stepName}>
          #{step.step_index} {AGENT_LABELS[step.agent_name] || step.agent_name}
        </span>
        <span className={styles.stepMetaInline}>
          {step.score != null && <em className={styles.score}>评分 {step.score}</em>}
          {step.model_name && step.model_name !== 'unknown' && (
            <em className={styles.model}>{step.model_name}</em>
          )}
          <span>{open ? '收起' : '展开'}</span>
        </span>
      </button>

      {open && (
        <div className={styles.stepBody}>
          <MetaBlock title="模型 / 成本 / 耗时">
            <span>{step.provider_name || '-'} · {step.model_name || '-'}</span>
            <span>tokens {step.input_tokens || 0}/{step.output_tokens || 0}</span>
            <span>{step.duration_seconds || 0}s</span>
          </MetaBlock>

          {Object.keys(dims).length > 0 && (
            <MetaBlock title="商业 Critic 维度分数">
              <div className={styles.dims}>
                {Object.entries(dims).map(([k, v]) => (
                  <span key={k} className={styles.dim}>{k}: {v}</span>
                ))}
              </div>
            </MetaBlock>
          )}

          {Array.isArray(meta.parallel_candidates) && meta.parallel_candidates.length > 0 && (
            <MetaBlock title="并行候选 / 选择理由">
              <ul className={styles.list}>
                {meta.parallel_candidates.map((c) => (
                  <li key={c.candidate_id} className={c.candidate_id === meta.selected_candidate_id ? styles.selected : ''}>
                    {c.candidate_id} · {c.strategy} · {c.score}
                    {c.candidate_id === meta.selected_candidate_id && ' ✓'}
                  </li>
                ))}
              </ul>
              {meta.selection_reason && <p className={styles.reason}>{meta.selection_reason}</p>}
            </MetaBlock>
          )}

          {Array.isArray(meta.critic_sources) && meta.critic_sources.length > 0 && (
            <MetaBlock title="并行 Critic 来源">{meta.critic_sources.join('、')}</MetaBlock>
          )}

          {Array.isArray(meta.memory_items) && meta.memory_items.length > 0 && (
            <MetaBlock title="召回的记忆">
              <ul className={styles.list}>
                {meta.memory_items.map((m, i) => (
                  <li key={i}>[{m.type}] #{m.id} · 相关度 {m.score}</li>
                ))}
              </ul>
            </MetaBlock>
          )}

  {readerRules.length > 0 && (
    <MetaBlock title="真人训练营规则引用">
      <ul className={styles.list}>
        {readerRules.map((r, i) => (
          <li key={i}>{typeof r === "string" ? r : JSON.stringify(r)}</li>
        ))}
      </ul>
    </MetaBlock>
  )}

          {step.input_prompt && (
            <MetaBlock title="输入 Prompt">
              <pre className={styles.pre}>{step.input_prompt}</pre>
            </MetaBlock>
          )}

          {step.raw_output && (
            <MetaBlock title="原始输出">
              <pre className={styles.pre}>{step.raw_output.slice(0, 4000)}</pre>
            </MetaBlock>
          )}
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

  useEffect(() => {
    setSseTaskId(id ? Number(id) : null);
  }, [id]);

  const fetchTask = useCallback(async () => {
    try {
      const res = await api.get(`/tasks/${id}`);
      setTask(res.data);
      setError('');
    } catch (err) {
      setError(err.response?.data?.detail || err.message || '加载任务详情失败');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchTask();
  }, [fetchTask]);

  if (loading) return <div className={styles.page}>加载中...</div>;
  if (error && !task) return <div className={styles.page}><p className={styles.err}>{error}</p></div>;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <Link to="/tasks" className={styles.back}>← 返回任务队列</Link>
        <h1>任务 #{task?.id}</h1>
        <div className={styles.progressWrap}>
          <ProgressIndicator taskId={sseTaskId} />
        </div>
        <div className={styles.summary}>
          <span>类型 {task?.task_type}</span>
          <span>状态 {task?.status}</span>
          <span>章节 {task?.chapter_id}</span>
          <span>成本 ${(task?.actual_cost || 0).toFixed?.(4) ?? task?.actual_cost ?? 0}</span>
        </div>
      </header>

      <ConfirmModal
        state={confirmState}
        onOk={handleOk}
        onCancel={handleCancel}
      />

      <section className={styles.steps}>
        <h2>Agent 执行步骤</h2>
        {(task.steps || []).length === 0 ? (
          <p className={styles.empty}>暂无步骤记录。</p>
        ) : (
          (task.steps || []).map((step) => <StepCard key={step.id} step={step} />)
        )}
      </section>
    </div>
  );
}

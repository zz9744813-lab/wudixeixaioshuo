/**
 * AgentDetailModal - 单个 Agent 详情弹窗
 *
 * Tabs:
 * - 绑定配置 (binding)
 * - 调度解释 (candidates + recent_routing_events)
 * - 运行统计 (recent_runs)
 */
import React, { useCallback, useEffect, useState } from 'react';
import api from '../../services/api';
import { toArray } from '../../utils/nullSafety';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { useConfirm } from '../../hooks/useConfirm';
import ConfirmModal from '../ConfirmModal';
import styles from './AgentMatrix.module.css';

export default function AgentDetailModal({ role, onClose, onUpdated, onToast }) {
  const [data, setData] = useState(null);
  const [providers, setProviders] = useState([]);
  const [tab, setTab] = useState('binding');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // 绑定表单
  const [mode, setMode] = useState('auto');
  const [fallbackEnabled, setFallbackEnabled] = useState(true);
  const [preferredQuality, setPreferredQuality] = useState('balanced');
  const [requireJson, setRequireJson] = useState(false);

  const { confirm, state: confirmState, handleOk, handleCancel } = useConfirm();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [cardRes, provRes] = await Promise.all([
        api.get(`/agent-model-configs/${role}`),
        api.get('/models/providers'),
      ]);
      const d = cardRes.data || {};
      setData(d);
      setProviders(toArray(provRes.data));
      // 同步表单
      setMode(d.assignment_mode || 'auto');
      setFallbackEnabled(d.fallback_enabled !== false);
      setPreferredQuality(d.preferred_quality || 'balanced');
      setRequireJson(Boolean(d.require_json));
    } catch (err) {
      onToast?.(`加载失败: ${err?.message || ''}`, 'danger');
    } finally {
      setLoading(false);
    }
  }, [role, onToast]);

  useEffect(() => { load(); }, [load]);

  const handleSaveBinding = async () => {
    setSaving(true);
    try {
      await api.put(`/agent-model-configs/${role}/binding`, {
        assignment_mode: mode,
        fallback_enabled: fallbackEnabled,
        preferred_quality: preferredQuality,
        require_json: requireJson,
        updated_by: 'user',
      });
      onToast?.('绑定已保存', 'success');
      onUpdated?.();
      onClose();
    } catch (err) {
      onToast?.(`保存失败: ${err?.response?.data?.detail || err?.message || ''}`, 'danger');
    } finally {
      setSaving(false);
    }
  };

  const handleResetToAuto = async () => {
    const ok = await confirm({
      title: '恢复自动分配',
      message: '确定将 ' + role + ' 恢复为自动分配？系统将根据健康/成本/能力自动选择模型。',
      confirmText: '确认',
      cancelText: '取消',
    });
    if (!ok) return;
    setSaving(true);
    try {
      await api.put(`/agent-model-configs/${role}/binding`, {
        assignment_mode: 'auto',
        fallback_enabled: true,
        preferred_quality: preferredQuality,
        require_json: requireJson,
        updated_by: 'user',
      });
      onToast?.('已恢复自动分配', 'success');
      onUpdated?.();
      onClose();
    } catch (err) {
      onToast?.(`恢复失败: ${err?.message || ''}`, 'danger');
    } finally {
      setSaving(false);
    }
  };

  if (loading || !data) {
    return (
      <Modal open onClose={onClose} title={`Agent: ${role}`} size="md">
        <div className={styles.empty}>加载中…</div>
      </Modal>
    );
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={`${data.name} (${data.agent_key})`}
      size="lg"
      footer={
        <div style={{ display: 'flex', gap: 8, justifyContent: 'space-between', width: '100%' }}>
          <Button variant="secondary" size="sm" onClick={onClose}>关闭</Button>
          {tab === 'binding' && (
            <div style={{ display: 'flex', gap: 8 }}>
              {mode === 'manual' && (
                <Button variant="ghost" size="sm" onClick={handleResetToAuto} disabled={saving}>
                  恢复自动
                </Button>
              )}
              <Button variant="primary" onClick={handleSaveBinding} disabled={saving}>
                {saving ? '保存中…' : '保存绑定'}
              </Button>
            </div>
          )}
        </div>
      }
    >
      {/* 顶部状态条 */}
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center', marginBottom: 12, fontSize: 12, color: 'var(--text-secondary)' }}>
        <span>Provider: <strong>{data.provider_name || '未配置'}</strong></span>
        <span>/</span>
        <span>Model: <strong>{data.model_name || '未选择'}</strong></span>
        <Badge variant={data.assignment_mode === 'manual' ? 'warning' : 'info'}>
          {data.assignment_mode === 'manual' ? 'LOCKED' : 'AUTO'}
        </Badge>
        <Badge variant={data.health === 'failed' ? 'danger' : data.health === 'warning' ? 'warning' : 'success'}>
          {data.health || 'unknown'}
        </Badge>
        {data.is_mock && <Badge variant="warning">MOCK</Badge>}
      </div>

      {data.assignment_mode === 'manual' && (
        <div className={styles.warning}>
          ℹ 当前 Agent 已手动锁定。"一键自动分配" 不会覆盖此配置，除非显式勾选 "同时覆盖手动锁定"。
        </div>
      )}

      {/* Tabs */}
      <div className={styles.detailTabs}>
        {[
          { key: 'binding', label: '绑定配置' },
          { key: 'candidates', label: `候选 (${toArray(data.candidates).length})` },
          { key: 'events', label: `调度历史 (${toArray(data.recent_routing_events).length})` },
          { key: 'runs', label: `运行统计 (${toArray(data.recent_runs).length})` },
        ].map(t => (
          <button
            key={t.key}
            type="button"
            className={`${styles.detailTab} ${tab === t.key ? styles.active : ''}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'binding' && (
        <BindingTab
          mode={mode}
          setMode={setMode}
          fallbackEnabled={fallbackEnabled}
          setFallbackEnabled={setFallbackEnabled}
          preferredQuality={preferredQuality}
          setPreferredQuality={setPreferredQuality}
          requireJson={requireJson}
          setRequireJson={setRequireJson}
          data={data}
        />
      )}

      {tab === 'candidates' && <CandidatesTab data={data} providers={providers} />}

      {tab === 'events' && <EventsTab data={data} />}

      {tab === 'runs' && <RunsTab data={data} />}

      <ConfirmModal state={confirmState} onOk={handleOk} onCancel={handleCancel} />
    </Modal>
  );
}


function BindingTab({ mode, setMode, fallbackEnabled, setFallbackEnabled, preferredQuality, setPreferredQuality, requireJson, setRequireJson, data }) {
  return (
    <div className={styles.bindingForm}>
      <div className={styles.bindingField}>
        <span>分配模式</span>
        <div className={styles.modeToggle}>
          <button type="button" className={mode === 'auto' ? styles.active : ''} onClick={() => setMode('auto')}>
            自动分配
          </button>
          <button type="button" className={mode === 'manual' ? styles.active : ''} onClick={() => setMode('manual')}>
            手动锁定
          </button>
        </div>
        <small style={{ color: 'var(--text-muted)', fontSize: 11, marginTop: 4 }}>
          {mode === 'auto'
            ? '系统按健康/成本/能力自动选择模型'
            : '锁定到当前 Provider/Model，全局自动分配不会覆盖'}
        </small>
      </div>

      <div className={styles.bindingField}>
        <span>角色偏好</span>
        <select value={preferredQuality} onChange={(e) => setPreferredQuality(e.target.value)}>
          <option value="cheap">低成本 (cheap)</option>
          <option value="fast">快速 (fast)</option>
          <option value="balanced">平衡 (balanced)</option>
          <option value="quality">高质量 (quality)</option>
          <option value="long_context">长上下文 (long_context)</option>
        </select>
      </div>

      <label className={`${styles.bindingField} ${styles.checkboxLabel}`} style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
        <input type="checkbox" checked={fallbackEnabled} onChange={(e) => setFallbackEnabled(e.target.checked)} />
        <span>手动锁定失败时允许回退</span>
      </label>

      <label className={`${styles.bindingField} ${styles.checkboxLabel}`} style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
        <input type="checkbox" checked={requireJson} onChange={(e) => setRequireJson(e.target.checked)} />
        <span>要求 JSON 输出</span>
      </label>

      {data.decision_reason && (
        <div className={styles.bindingField}>
          <span>当前调度理由</span>
          <div style={{ padding: 8, background: 'var(--bg-sunken)', borderRadius: 6, fontSize: 12 }}>
            {data.decision_reason}
          </div>
        </div>
      )}
    </div>
  );
}


function CandidatesTab({ data, providers }) {
  const candidates = toArray(data.candidates);
  if (candidates.length === 0) {
    return <div className={styles.empty}>该 Agent 暂无可用候选。请先在 /llm-routes 添加路由。</div>;
  }
  return (
    <table className={styles.candidateTable}>
      <thead>
        <tr>
          <th>Provider</th>
          <th>Model</th>
          <th>优先级</th>
          <th>健康</th>
          <th>延迟</th>
          <th>分数</th>
          <th>状态</th>
        </tr>
      </thead>
      <tbody>
        {candidates.map((c) => (
          <tr key={c.route_id || c.provider_id}>
            <td>{c.provider_name || '-'}</td>
            <td><code style={{ fontSize: 11 }}>{c.model_name || '-'}</code></td>
            <td>{c.priority}</td>
            <td>
              {c.is_circuit_open
                ? <Badge variant="danger">熔断</Badge>
                : c.stats?.total_calls > 0
                ? `${(c.stats.success_rate || 0).toFixed(0)}%`
                : <span style={{ color: 'var(--text-muted)' }}>新</span>}
            </td>
            <td>{c.stats?.avg_latency_ms ? `${c.stats.avg_latency_ms}ms` : '-'}</td>
            <td>
              <span className={styles.scoreBar} style={{ width: `${c.score || 0}%` }} />
              <strong>{c.score || 0}</strong>
            </td>
            <td>
              {c.enabled
                ? c.is_circuit_open
                  ? <Badge variant="danger">熔断</Badge>
                  : <Badge variant="success">启用</Badge>
                : <Badge variant="muted">禁用</Badge>}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}


function EventsTab({ data }) {
  const events = toArray(data.recent_routing_events);
  if (events.length === 0) {
    return <div className={styles.empty}>该 Agent 暂无调度历史</div>;
  }
  return (
    <div className={styles.eventList}>
      {events.map((e) => (
        <div key={e.id} className={styles.eventItem}>
          <div className={styles.head}>
            <span>{e.selected_provider_name || '-'} / {e.selected_model_name || '-'}</span>
            <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>{e.created_at}</span>
          </div>
          <div className={styles.reason}>{e.decision_reason || '-'}</div>
          {e.fallback_used && <div className={styles.fallback}>使用了回退链</div>}
        </div>
      ))}
    </div>
  );
}


function RunsTab({ data }) {
  const runs = toArray(data.recent_runs);
  if (runs.length === 0) {
    return <div className={styles.empty}>该 Agent 暂无运行记录</div>;
  }
  return (
    <table className={styles.candidateTable}>
      <thead>
        <tr>
          <th>时间</th>
          <th>模型</th>
          <th>状态</th>
          <th>In/Out</th>
          <th>成本</th>
          <th>延迟</th>
        </tr>
      </thead>
      <tbody>
        {runs.map((r) => (
          <tr key={r.id}>
            <td style={{ fontSize: 11, color: 'var(--text-muted)' }}>{r.started_at?.slice(11, 19) || '-'}</td>
            <td><code style={{ fontSize: 11 }}>{r.model_name || '-'}</code></td>
            <td>
              <Badge variant={r.status === 'success' ? 'success' : r.status === 'failed' ? 'danger' : 'muted'}>
                {r.status || 'unknown'}
              </Badge>
            </td>
            <td>{r.input_tokens || 0} / {r.output_tokens || 0}</td>
            <td>${Number(r.estimated_cost || 0).toFixed(4)}</td>
            <td>{r.duration_ms ? `${r.duration_ms}ms` : '-'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

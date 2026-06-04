/**
 * AgentMatrix - 模型调度中心 Agent 矩阵组件
 *
 * 展示 18 个 agent（按 4 个 category 分组），每个 agent 显示:
 * - 名称 / 角色
 * - AUTO / LOCKED 标签
 * - 当前 Provider / Model
 * - 健康状态 / Mock 警告
 * - 调度理由
 *
 * 点击 Agent 卡片 → 弹出 AgentDetailModal
 * 顶部 "一键自动分配" 按钮 → 弹 AutoAssignModal（dry-run 预览 → 确认落库）
 */
import React, { useCallback, useEffect, useState } from 'react';
import api from '../../services/api';
import { toArray } from '../../utils/nullSafety';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import AgentDetailModal from './AgentDetailModal';
import AutoAssignModal from './AutoAssignModal';
import styles from './AgentMatrix.module.css';

const STATUS_VARIANT = {
  healthy: 'success',
  warning: 'warning',
  failed: 'danger',
  unconfigured: 'muted',
  disabled: 'muted',
};

const HEALTH_LABEL = {
  healthy: '健康',
  warning: '警告',
  failed: '失败',
  unconfigured: '未配置',
  disabled: '已禁用',
};

export default function AgentMatrix({ onToast }) {
  const [data, setData] = useState({
    summary: { agent_count: 0, auto_count: 0, manual_count: 0, today_cost_usd: 0 },
    groups: [],
    providers: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [selectedRole, setSelectedRole] = useState(null);
  const [showAutoAssign, setShowAutoAssign] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.get('/agent-model-configs');
      const d = res.data || {};
      setData({
        summary: d.summary || { agent_count: 0, auto_count: 0, manual_count: 0, today_cost_usd: 0 },
        groups: toArray(d.groups),
        providers: toArray(d.providers),
      });
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.message || '加载失败';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleAutoAssigned = useCallback(() => {
    setShowAutoAssign(false);
    fetchData();
    onToast?.('自动分配完成', 'success');
  }, [fetchData, onToast]);

  const handleBindingUpdated = useCallback(() => {
    fetchData();
    onToast?.('绑定已更新', 'success');
  }, [fetchData, onToast]);

  const summary = data.summary || {};
  const groups = toArray(data.groups);
  const totalFailed = (summary.failed_count || 0);

  return (
    <div className={styles.matrix}>
      {/* 工具栏 */}
      <div className={styles.toolbar}>
        <Button
          variant="primary"
          size="sm"
          onClick={() => setShowAutoAssign(true)}
          disabled={loading}
        >
          一键自动分配
        </Button>
        <Button
          variant="secondary"
          size="sm"
          onClick={fetchData}
          disabled={loading}
        >
          {loading ? '加载中…' : '刷新'}
        </Button>
        <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--text-muted)' }}>
          调度中心 · {summary.agent_count || 0} 个 Agent
        </span>
      </div>

      {/* 概览条 */}
      <div className={styles.summaryBar}>
        <div className={styles.summaryCell}>
          <span>Agent 总数</span>
          <strong>{summary.agent_count || 0}</strong>
        </div>
        <div className={styles.summaryCell}>
          <span>自动分配</span>
          <strong className={styles.success}>{summary.auto_count || 0}</strong>
        </div>
        <div className={styles.summaryCell}>
          <span>手动锁定</span>
          <strong className={styles.warning}>{summary.manual_count || 0}</strong>
        </div>
        <div className={styles.summaryCell}>
          <span>失败</span>
          <strong className={totalFailed > 0 ? styles.danger : ''}>{totalFailed}</strong>
        </div>
        <div className={styles.summaryCell}>
          <span>今日成本</span>
          <strong>${Number(summary.today_cost_usd || 0).toFixed(3)}</strong>
        </div>
        <div className={styles.summaryCell}>
          <span>Token 24h</span>
          <strong>{(Number(summary.today_input_tokens || 0) + Number(summary.today_output_tokens || 0)).toLocaleString()}</strong>
        </div>
      </div>

      {error && <div className={styles.errorText}>{error}</div>}

      {/* 分组卡片 */}
      {groups.map((group) => (
        <div key={group.category} className={styles.groupBlock}>
          <div className={styles.groupHeader}>
            <span>{group.title || group.category}</span>
            <span className={styles.count}>
              ({toArray(group.agents).length} 个 agent)
            </span>
          </div>
          <div className={styles.cardGrid}>
            {toArray(group.agents).map((agent) => (
              <AgentCard
                key={agent.agent_key}
                agent={agent}
                selected={selectedRole === agent.agent_key}
                onSelect={() => setSelectedRole(agent.agent_key)}
              />
            ))}
          </div>
        </div>
      ))}

      {/* 详情弹窗 */}
      {selectedRole && (
        <AgentDetailModal
          role={selectedRole}
          onClose={() => setSelectedRole(null)}
          onUpdated={handleBindingUpdated}
          onToast={onToast}
        />
      )}

      {/* 一键自动分配弹窗 */}
      {showAutoAssign && (
        <AutoAssignModal
          onClose={() => setShowAutoAssign(false)}
          onCompleted={handleAutoAssigned}
          onToast={onToast}
        />
      )}
    </div>
  );
}


function AgentCard({ agent, selected, onSelect }) {
  const healthClass = agent.health === 'failed'
    ? styles['health-failed']
    : agent.health === 'warning'
    ? styles['health-warning']
    : '';

  const cardClass = [
    styles.agentCard,
    selected ? styles.selected : '',
    healthClass,
    agent.is_mock ? styles['is-mock'] : '',
    agent.status === 'unconfigured' ? styles.unconfigured : '',
  ].filter(Boolean).join(' ');

  const modeVariant = agent.assignment_mode === 'manual' ? 'warning' : 'info';
  const modeLabel = agent.assignment_mode === 'manual' ? 'LOCKED' : 'AUTO';

  return (
    <button type="button" className={cardClass} onClick={onSelect}>
      <div className={styles.cardRow}>
        <div className={styles.cardName}>
          <span className={styles.cardAvatar}>
            {(agent.name || agent.agent_key).charAt(0)}
          </span>
          <span>{agent.name || agent.agent_key}</span>
        </div>
        <Badge variant={modeVariant} size="sm">{modeLabel}</Badge>
      </div>

      <div className={styles.cardRole}>role: {agent.agent_key}</div>

      <div className={styles.cardModel}>
        <span>{agent.provider_name || '—'}</span>
        <span className={styles.sep}>/</span>
        <strong>{agent.model_name || '未选择'}</strong>
        {agent.is_mock && <Badge variant="warning" size="sm">MOCK</Badge>}
      </div>

      <div className={styles.cardMeta}>
        <span className={styles.metaItem}>
          <Badge variant={STATUS_VARIANT[agent.health] || 'muted'} size="sm">
            {HEALTH_LABEL[agent.health] || agent.health || 'unknown'}
          </Badge>
        </span>
        {agent.avg_latency_ms != null && (
          <span className={styles.metaItem}>{agent.avg_latency_ms}ms</span>
        )}
        <span className={styles.metaItem}>
          ${Number(agent.today_cost_usd || 0).toFixed(3)}
        </span>
        {agent.calls_24h > 0 && (
          <span className={styles.metaItem}>{agent.calls_24h} calls/24h</span>
        )}
      </div>

      {agent.is_mock && (
        <div className={styles.cardMockWarn}>⚠ Mock 模型，仅测试用</div>
      )}

      {agent.decision_reason && (
        <div className={styles.cardReason} title={agent.decision_reason}>
          {agent.decision_reason}
        </div>
      )}
    </button>
  );
}

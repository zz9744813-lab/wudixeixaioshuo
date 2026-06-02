import React, { useCallback, useEffect, useState } from 'react';
import api, { getApiErrorMessage } from '../services/api';
import { toArray } from '../utils/nullSafety';
import { useToast } from '../contexts/ToastContext';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import PageHeader from '../components/console/PageHeader';
import StatusPill from '../components/console/StatusPill';
import SectionCard from '../components/console/SectionCard';
import styles from './AgentModelAssign.module.css';

const PAGE_TITLE = '🤖 Agent 模型分配';
const PAGE_SUBTITLE = '为每个 Agent 角色独立分配模型、温度、最大 Token 等参数';

export default function AgentModelAssign() {
  const [assignments, setAssignments] = useState([]);
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [testingRole, setTestingRole] = useState(null);
  const [testResults, setTestResults] = useState({});

  // 编辑状态：{ role: { provider_id, model_name, temperature, max_tokens, timeout_seconds, max_retries, changed } }
  const [edits, setEdits] = useState({});

  const toast = useToast();

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.get('/model-assignments/');
      const data = res.data;
      setAssignments(data.assignments || []);
      setProviders(data.providers || []);
      // 初始化编辑状态（用 defaults 兜底，防止后端历史 NULL 数据传到前端
      // 后输入框显示空白或 NaN）
      const initialEdits = {};
      (data.assignments || []).forEach((a) => {
        const defaults = a.defaults || { temperature: 0.5, max_tokens: 4000 };
        initialEdits[a.role] = {
          provider_id: a.provider_id || '',
          model_name: a.model_name || '',
          temperature: a.temperature ?? defaults.temperature,
          max_tokens: a.max_tokens ?? defaults.max_tokens,
          timeout_seconds: a.timeout_seconds || 60,
          max_retries: a.max_retries || 2,
          changed: false,
        };
      });
      setEdits(initialEdits);
    } catch (err) {
      const msg = getApiErrorMessage(err);
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleEdit = (role, field, value) => {
    setEdits((prev) => ({
      ...prev,
      [role]: {
        ...prev[role],
        [field]: value,
        changed: true,
      },
    }));
  };

  const handleProviderChange = (role, providerId) => {
    const prov = providers.find((p) => Number(p.id) === Number(providerId));
    setEdits((prev) => ({
      ...prev,
      [role]: {
        ...prev[role],
        provider_id: Number(providerId),
        model_name: prov?.default_model || prev[role]?.model_name || '',
        changed: true,
      },
    }));
  };

  const handleSave = async (role) => {
    const e = edits[role];
    if (!e || !e.provider_id || !e.model_name) {
      toast.error(`角色 "${role}" 需要选择 Provider 和模型名`);
      return;
    }
    setSaving(true);
    try {
      await api.put(`/model-assignments/${role}`, {
        provider_id: e.provider_id,
        model_name: e.model_name,
        temperature: e.temperature,
        max_tokens: e.max_tokens,
        timeout_seconds: e.timeout_seconds,
        max_retries: e.max_retries,
      });
      toast.success(`角色 "${role}" 保存成功`);
      // 标记为未修改
      setEdits((prev) => ({
        ...prev,
        [role]: { ...prev[role], changed: false },
      }));
      // 刷新数据
      await fetchData();
    } catch (err) {
      const msg = getApiErrorMessage(err);
      toast.error(msg, 6000);
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async (role) => {
    setTestingRole(role);
    try {
      const res = await api.post(`/model-assignments/${role}/test`);
      setTestResults((prev) => ({
        ...prev,
        [role]: { status: 'success', message: `连接成功 — 模型: ${res.data?.model_used || res.data?.model_name}`, response: res.data?.response_preview },
      }));
      toast.success(`角色 "${role}" 测试成功`);
    } catch (err) {
      const detail = err?.response?.data;
      const msg = detail?.message || detail?.detail || err.message || '测试失败';
      setTestResults((prev) => ({
        ...prev,
        [role]: { status: 'failed', message: msg },
      }));
      toast.error(`角色 "${role}" 测试失败: ${msg}`, 6000);
    } finally {
      setTestingRole(null);
    }
  };

  const handleDelete = async (role) => {
    if (!window.confirm(`确定要删除角色 "${role}" 的模型分配吗？`)) return;
    try {
      await api.delete(`/model-assignments/${role}`);
      toast.success(`角色 "${role}" 分配已删除`);
      await fetchData();
    } catch (err) {
      const msg = getApiErrorMessage(err);
      toast.error(msg, 6000);
    }
  };

  // 一键应用推荐默认值
  const handleApplyDefaults = () => {
    setEdits((prev) => {
      const next = { ...prev };
      assignments.forEach((a) => {
        const defaults = a.defaults || {};
        next[a.role] = {
          ...next[a.role],
          temperature: defaults.temperature !== undefined ? defaults.temperature : 0.5,
          max_tokens: defaults.max_tokens !== undefined ? defaults.max_tokens : 4000,
          changed: true,
        };
      });
      return next;
    });
    toast.info('已填充推荐默认值，请逐一保存各角色');
  };

  const roleLabel = (role) => {
    const map = {
      planner: '📋 规划者', draft: '✍️ 起草者', critic: '🔍 评审者',
      rewrite: '🔄 改写者', continuity: '🔗 一致性检查', learning: '📖 学习者',
      study: '📊 学习分析', split: '✂️ 拆分者', analyze: '🧪 分析者',
      memory_update: '💾 记忆更新', memory_retrieval: '🔎 记忆检索',
      foreshadow: '🎭 伏笔管理', logic_critic: '🧠 逻辑评审',
      style_critic: '🎨 风格评审', commercial_critic: '💰 商业评审',
      default: '⚙️ 默认',
    };
    return map[role] || role;
  };

  if (loading) {
    return (
      <div className={styles.page}>
        <PageHeader title={PAGE_TITLE} subtitle="加载中..." />
        <div className={styles.loading}>加载中...</div>
      </div>
    );
  }

  if (error && assignments.length === 0) {
    return (
      <div className={styles.page}>
        <PageHeader title={PAGE_TITLE} subtitle="加载失败" status={<StatusPill status="danger" label="错误" />} />
        <div className={styles.error}>
          <strong>加载失败</strong>
          <p>{error}</p>
          <Button variant="secondary" size="sm" onClick={fetchData}>重试</Button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <PageHeader
        title={PAGE_TITLE}
        subtitle={PAGE_SUBTITLE}
        status={<StatusPill status="success" label={`${assignments.filter(a => a.configured).length}/${assignments.length} 已配置`} />}
      />

      <SectionCard title="批量操作" actions={
        <Button variant="secondary" size="sm" onClick={handleApplyDefaults}>
          填充推荐默认值
        </Button>
      }>
        <p className={styles.hint}>
          每个 Agent 角色可以独立选择 Provider、模型、温度、最大 Token 等参数。修改某个角色不会影响其他角色。
          <br />点击"填充推荐默认值"会自动填入各角色的推荐温度和 Token 参数，但仍需对各角色逐一保存。
        </p>
      </SectionCard>

      <SectionCard title="Agent 角色分配">
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>角色</th>
                <th>Provider</th>
                <th>模型</th>
                <th>温度</th>
                <th>Max Tokens</th>
                <th>超时(s)</th>
                <th>重试</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {assignments.map((a) => {
                const e = edits[a.role] || {};
                const result = testResults[a.role];
                const hasChange = e.changed;
                return (
                  <tr key={a.role} className={hasChange ? styles.rowChanged : ''}>
                    <td>
                      <div className={styles.roleCell}>
                        <span className={styles.roleLabel}>{roleLabel(a.role)}</span>
                        <code className={styles.roleCode}>{a.role}</code>
                      </div>
                    </td>
                    <td>
                      <select
                        className={styles.select}
                        value={e.provider_id || ''}
                        onChange={(ev) => handleProviderChange(a.role, ev.target.value)}
                      >
                        <option value="">未配置</option>
                        {providers.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.name} ({p.provider_type})
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <input
                        className={styles.input}
                        value={e.model_name || ''}
                        onChange={(ev) => handleEdit(a.role, 'model_name', ev.target.value)}
                        placeholder="模型名"
                      />
                    </td>
                    <td>
                      <input
                        className={styles.inputSmall}
                        type="number"
                        step="0.1"
                        min="0"
                        max="2"
                        value={e.temperature ?? 0.7}
                        onChange={(ev) => handleEdit(a.role, 'temperature', parseFloat(ev.target.value) || 0)}
                      />
                    </td>
                    <td>
                      <input
                        className={styles.inputSmall}
                        type="number"
                        min="100"
                        max="32000"
                        value={e.max_tokens ?? 4000}
                        onChange={(ev) => handleEdit(a.role, 'max_tokens', parseInt(ev.target.value) || 4000)}
                      />
                    </td>
                    <td>
                      <input
                        className={styles.inputSmall}
                        type="number"
                        min="10"
                        max="600"
                        value={e.timeout_seconds ?? 60}
                        onChange={(ev) => handleEdit(a.role, 'timeout_seconds', parseInt(ev.target.value) || 60)}
                      />
                    </td>
                    <td>
                      <input
                        className={styles.inputSmall}
                        type="number"
                        min="0"
                        max="10"
                        value={e.max_retries ?? 2}
                        onChange={(ev) => handleEdit(a.role, 'max_retries', parseInt(ev.target.value) || 2)}
                      />
                    </td>
                    <td>
                      {a.configured ? (
                        <Badge variant="success">已配置</Badge>
                      ) : (
                        <Badge variant="muted">未配置</Badge>
                      )}
                      {result && (
                        <div className={`${styles.testResult} ${result.status === 'success' ? styles.testOk : styles.testFail}`}>
                          {result.message?.slice(0, 40)}
                        </div>
                      )}
                    </td>
                    <td className={styles.actions}>
                      <Button
                        variant="primary"
                        size="sm"
                        disabled={saving || !e.provider_id || !e.model_name}
                        onClick={() => handleSave(a.role)}
                      >
                        保存
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        disabled={testingRole === a.role || !a.configured}
                        onClick={() => handleTest(a.role)}
                      >
                        {testingRole === a.role ? '测试中…' : '测试'}
                      </Button>
                      {a.configured && (
                        <Button variant="danger" size="sm" onClick={() => handleDelete(a.role)}>删除</Button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </SectionCard>
    </div>
  );
}
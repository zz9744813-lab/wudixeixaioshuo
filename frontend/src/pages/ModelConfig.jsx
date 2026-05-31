import React, { useCallback, useEffect, useState } from 'react';
import { useFetch } from '../hooks/useFetch';
import api from '../services/api';
import { useToast } from '../contexts/ToastContext';
import { useConfirm } from '../hooks/useConfirm';
import { Icon } from '../components/ui/Icon';
import { AsyncState } from '../components/ui/AsyncState';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import ConfirmModal from '../components/ConfirmModal';
import styles from './ModelConfig.module.css';

const PAGE_TITLE = '⚙️ 模型配置中心';
const PAGE_ICON = 'Settings';

const PROVIDER_TYPES = [
  { value: 'openai', label: 'OpenAI 兼容' },
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'gemini', label: 'Google Gemini' },
  { value: 'openrouter', label: 'OpenRouter' },
  { value: 'custom', label: '自定义' },
];

export default function ModelConfig() {
  const [providers, setProviders] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showProviderModal, setShowProviderModal] = useState(false);
  const [showQuickSetup, setShowQuickSetup] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [testingId, setTestingId] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  // Form state
  const [name, setName] = useState('');
  const [providerType, setProviderType] = useState('openai');
  const [baseUrl, setBaseUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [defaultModel, setDefaultModel] = useState('');
  const [isEnabled, setIsEnabled] = useState(true);

  // Quick setup form
  const [qsName, setQsName] = useState('默认配置');
  const [qsType, setQsType] = useState('openai');
  const [qsUrl, setQsUrl] = useState('');
  const [qsKey, setQsKey] = useState('');
  const [qsModel, setQsModel] = useState('gpt-3.5-turbo');

  const toast = useToast();
  const { confirm, state: confirmState, handleOk, handleCancel } = useConfirm();

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [pRes, rRes] = await Promise.all([
        api.get('/models/providers'),
        api.get('/models/roles'),
      ]);
      setProviders(Array.isArray(pRes.data) ? pRes.data : []);
      setRoles(Array.isArray(rRes.data) ? rRes.data : []);
    } catch (err) {
      const msg = err?.response?.data?.detail || err.message || '加载失败';
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const resetForm = () => {
    setName(''); setProviderType('openai'); setBaseUrl('');
    setApiKey(''); setDefaultModel(''); setIsEnabled(true); setEditingId(null);
  };

  const handleOpenProvider = () => { resetForm(); setShowProviderModal(true); };
  const handleEdit = (p) => {
    setEditingId(p.id);
    setName(p.name); setProviderType(p.provider_type);
    setBaseUrl(p.base_url); setDefaultModel(p.default_model);
    setIsEnabled(p.is_enabled); setApiKey('');
    setShowProviderModal(true);
  };

  const handleSaveProvider = async () => {
    if (!name.trim() || !baseUrl.trim() || !defaultModel.trim()) {
      toast.error('请填写名称、Base URL 和默认模型', 4000);
      return;
    }
    setSubmitting(true);
    try {
      const payload = {
        name: name.trim(),
        provider_type: providerType,
        base_url: baseUrl.trim(),
        api_key: apiKey || undefined,
        default_model: defaultModel.trim(),
        is_enabled: isEnabled,
      };
      if (editingId) {
        await api.put(`/models/providers/${editingId}`, payload);
        toast.success('提供商已更新');
      } else {
        await api.post('/models/providers', payload);
        toast.success('提供商已创建');
      }
      setShowProviderModal(false);
      fetchAll();
    } catch (err) {
      const msg = err?.response?.data?.detail || err.message || '保存失败';
      toast.error(msg, 6000);
    } finally { setSubmitting(false); }
  };

  const handleDelete = async () => {
    const ok = await confirm({ title: '删除 Provider', message: '确定要删除此 Provider 吗？相关角色映射也会受影响。' });
    if (!ok) return;
    try {
      await api.del(`/models/providers/${confirmState?.id || editingId}`);
      toast.success('Provider 已删除');
      fetchAll();
    } catch (err) {
      const msg = err?.response?.data?.detail || err.message || '删除失败';
      toast.error(msg, 6000);
    }
  };

  const handleTest = async (id) => {
    setTestingId(id);
    try {
      const res = await api.post(`/models/providers/${id}/test`);
      toast.success('连接测试成功', 4000);
      fetchAll();
    } catch (err) {
      const detail = err?.response?.data;
      const msg = detail?.message || detail?.detail || err.message || '测试失败';
      toast.error(`连接失败: ${msg}`, 6000);
    } finally { setTestingId(null); }
  };

  const handleQuickSetup = async () => {
    if (!qsUrl.trim() || !qsKey.trim() || !qsModel.trim()) {
      toast.error('请填写 URL、API Key 和默认模型', 4000);
      return;
    }
    setSubmitting(true);
    try {
      const res = await api.post('/models/quick-setup', {
        name: qsName.trim() || '默认配置',
        provider_type: qsType,
        base_url: qsUrl.trim(),
        api_key: qsKey.trim(),
        default_model: qsModel.trim(),
      });
      toast.success(`配置成功：已配置 ${res.data?.roles_configured?.length || 16} 个角色`, 5000);
      setShowQuickSetup(false);
      fetchAll();
    } catch (err) {
      const msg = err?.response?.data?.detail || err.message || '配置失败';
      toast.error(msg, 6000);
    } finally { setSubmitting(false); }
  };

  const typeLabel = (t) => (PROVIDER_TYPES.find((x) => x.value === t)?.label) || t;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}><Icon name={PAGE_ICON} size={22} /><span>{PAGE_TITLE}</span></h1>
      </header>

      {/* Quick Setup */}
      <section className={styles.card}>
        <h2 className={styles.cardTitle}>⚡ 快速配置中转站</h2>
        {!showQuickSetup ? (
          <div className={styles.quickRow}>
            <span className={styles.quickHint}>一键配置所有角色模型映射，只需提供一个 API Key。</span>
            <Button variant="primary" onClick={() => { setQsName('默认配置'); setQsType('openai'); setQsUrl(''); setQsKey(''); setQsModel('gpt-3.5-turbo'); setShowQuickSetup(true); }}>一键快速配置</Button>
          </div>
        ) : (
          <div className={styles.formGrid}>
            <label>
              <span>配置名</span>
              <input value={qsName} onChange={(e) => setQsName(e.target.value)} placeholder="默认配置" />
            </label>
            <label>
              <span>Provider 类型</span>
              <select value={qsType} onChange={(e) => { setQsType(e.target.value); if (e.target.value === 'openai') setQsUrl('https://api.openai.com/v1'); else if (e.target.value === 'anthropic') setQsUrl('https://api.anthropic.com'); else setQsUrl('http://localhost:8000/v1'); }}>
                {PROVIDER_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </label>
            <label>
              <span>Base URL</span>
              <input value={qsUrl} onChange={(e) => setQsUrl(e.target.value)} placeholder="https://api.openai.com/v1" />
            </label>
            <label>
              <span>API Key</span>
              <input value={qsKey} onChange={(e) => setQsKey(e.target.value)} type="password" placeholder="sk-..." />
            </label>
            <label>
              <span>默认模型</span>
              <input value={qsModel} onChange={(e) => setQsModel(e.target.value)} placeholder="gpt-3.5-turbo" />
            </label>
            <div className={styles.formActions}>
              <Button variant="primary" onClick={handleQuickSetup} disabled={submitting}>{submitting ? '配置中…' : '一键保存并配置所有角色'}</Button>
              <Button variant="secondary" onClick={() => setShowQuickSetup(false)}>取消</Button>
            </div>
          </div>
        )}
      </section>

      {/* Provider List */}
      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <h2 className={styles.cardTitle}>📡 Provider 列表</h2>
          <Button variant="primary" size="sm" onClick={handleOpenProvider}>+ 新增 Provider</Button>
        </div>
        <AsyncState loading={loading} error={error} onRetry={fetchAll} isEmpty={providers.length === 0} emptyTitle="暂无 Provider，请先添加或快速配置">
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>名称</th><th>类型</th><th>Base URL</th><th>默认模型</th><th>启用</th><th>最后测试</th><th>操作</th>
                </tr>
              </thead>
              <tbody>
                {providers.map((p) => (
                  <tr key={p.id}>
                    <td>{p.name}</td>
                    <td><Badge variant="muted">{typeLabel(p.provider_type)}</Badge></td>
                    <td><span className={styles.mono}>{p.base_url}</span></td>
                    <td>{p.default_model}</td>
                    <td><Badge variant={p.is_enabled ? 'success' : 'danger'}>{p.is_enabled ? '是' : '否'}</Badge></td>
                    <td>
                      {p.last_test_result ? (
                        <Badge variant={p.last_test_result === 'success' ? 'success' : 'danger'}>{p.last_test_result === 'success' ? '成功' : '失败'}</Badge>
                      ) : <span className={styles.muted}>未测试</span>}
                    </td>
                    <td className={styles.actions}>
                      <Button variant="ghost" size="sm" onClick={() => handleTest(p.id)} disabled={testingId === p.id}>
                        {testingId === p.id ? '测试中…' : '测试'}
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => handleEdit(p)}>编辑</Button>
                      <Button variant="danger" size="sm" onClick={() => { setEditingId(p.id); handleDelete(); }}>删除</Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </AsyncState>
      </section>

      {/* Role Mapping */}
      <section className={styles.card}>
        <h2 className={styles.cardTitle}>🔗 角色模型映射</h2>
        <AsyncState loading={loading} error={null} isEmpty={roles.length === 0} emptyTitle="暂无角色映射" hideLoading>
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr><th>Role</th><th>Provider</th><th>模型</th><th>Temperature</th><th>Max Tokens</th></tr>
              </thead>
              <tbody>
                {roles.map((r) => (
                  <tr key={r.id}>
                    <td><code className={styles.mono}>{r.role}</code></td>
                    <td>{r.provider?.name || '-'}</td>
                    <td>{r.model_name}</td>
                    <td>{r.temperature}</td>
                    <td>{r.max_tokens}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </AsyncState>
      </section>

      {/* Provider Edit/Create Modal */}
      <Modal open={showProviderModal} onClose={() => setShowProviderModal(false)} title={editingId ? '编辑 Provider' : '新增 Provider'} size="md" footer={
        <div className={styles.modalActions}>
          <Button variant="primary" onClick={handleSaveProvider} disabled={submitting}>{submitting ? '保存中…' : '保存'}</Button>
          <Button variant="secondary" onClick={() => setShowProviderModal(false)}>取消</Button>
        </div>
      }>
        <div className={styles.formGrid}>
          <label>
            <span>名称 *</span>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="My OpenAI" />
          </label>
          <label>
            <span>Provider 类型 *</span>
            <select value={providerType} onChange={(e) => setProviderType(e.target.value)}>
              {PROVIDER_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </label>
          <label>
            <span>Base URL *</span>
            <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="https://api.openai.com/v1" />
          </label>
          <label>
            <span>API Key（留空不修改）</span>
            <input value={apiKey} onChange={(e) => setApiKey(e.target.value)} type="password" placeholder={editingId ? '留空不修改' : 'sk-...'} />
          </label>
          <label>
            <span>默认模型 *</span>
            <input value={defaultModel} onChange={(e) => setDefaultModel(e.target.value)} placeholder="gpt-4o-mini" />
          </label>
          <label className={styles.checkLabel}>
            <input type="checkbox" checked={isEnabled} onChange={(e) => setIsEnabled(e.target.checked)} />
            <span>启用</span>
          </label>
        </div>
      </Modal>

      <ConfirmModal state={confirmState} onOk={handleOk} onCancel={handleCancel} />
    </div>
  );
}

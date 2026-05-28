import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../services/api';
import './ModelConfig.css';

function ModelConfig() {
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [newProvider, setNewProvider] = useState({
    name: '',
    provider_type: 'openai',
    base_url: 'https://api.openai.com/v1',
    api_key: '',
    default_model: 'gpt-3.5-turbo',
  });

  useEffect(() => {
    fetchProviders();
  }, []);

  const fetchProviders = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/models/providers`);
      const data = await response.json();
      setProviders(data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching providers:', error);
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch(`${API_BASE_URL}/models/providers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newProvider),
      });
      if (response.ok) {
        setShowForm(false);
        setNewProvider({
          name: '',
          provider_type: 'openai',
          base_url: 'https://api.openai.com/v1',
          api_key: '',
          default_model: 'gpt-3.5-turbo',
        });
        fetchProviders();
      }
    } catch (error) {
      console.error('Error creating provider:', error);
    }
  };

  const handleTest = async (id) => {
    try {
      const response = await fetch(`${API_BASE_URL}/models/providers/${id}/test`, {
        method: 'POST',
      });
      const data = await response.json();
      alert(data.message);
      fetchProviders();
    } catch (error) {
      console.error('Error testing provider:', error);
    }
  };

  if (loading) {
    return <div className="loading">加载中...</div>;
  }

  return (
    <div className="model-config-page">
      <header className="page-header">
        <h1>⚙️ 模型配置中心</h1>
        <button className="btn-primary" onClick={() => setShowForm(true)}>
          ➕ 添加 Provider
        </button>
      </header>

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>添加模型提供商</h2>
            <form onSubmit={handleCreate}>
              <div className="form-group">
                <label>名称</label>
                <input
                  type="text"
                  value={newProvider.name}
                  onChange={(e) => setNewProvider({ ...newProvider, name: e.target.value })}
                  placeholder="如：OpenAI"
                  required
                />
              </div>
              <div className="form-group">
                <label>类型</label>
                <select
                  value={newProvider.provider_type}
                  onChange={(e) => setNewProvider({ ...newProvider, provider_type: e.target.value })}
                >
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                  <option value="gemini">Gemini</option>
                  <option value="openrouter">OpenRouter</option>
                  <option value="custom">自定义</option>
                </select>
              </div>
              <div className="form-group">
                <label>Base URL</label>
                <input
                  type="text"
                  value={newProvider.base_url}
                  onChange={(e) => setNewProvider({ ...newProvider, base_url: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>API Key</label>
                <input
                  type="password"
                  value={newProvider.api_key}
                  onChange={(e) => setNewProvider({ ...newProvider, api_key: e.target.value })}
                  placeholder="sk-..."
                />
              </div>
              <div className="form-group">
                <label>默认模型</label>
                <input
                  type="text"
                  value={newProvider.default_model}
                  onChange={(e) => setNewProvider({ ...newProvider, default_model: e.target.value })}
                  required
                />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowForm(false)}>
                  取消
                </button>
                <button type="submit" className="btn-primary">
                  保存
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="providers-list">
        {providers.length === 0 ? (
          <div className="empty-state">
            <p>暂无配置</p>
            <p className="hint">添加 LLM Provider 以启用真实生成功能</p>
          </div>
        ) : (
          providers.map((provider) => (
            <div key={provider.id} className="provider-card">
              <div className="provider-header">
                <h3>{provider.name}</h3>
                <span className={`status ${provider.is_enabled ? 'enabled' : 'disabled'}`}>
                  {provider.is_enabled ? '已启用' : '已禁用'}
                </span>
              </div>
              <div className="provider-info">
                <p><label>类型:</label> {provider.provider_type}</p>
                <p><label>Base URL:</label> {provider.base_url}</p>
                <p><label>默认模型:</label> {provider.default_model}</p>
                <p><label>上次测试:</label> {provider.last_test_result || '未测试'}</p>
              </div>
              <div className="provider-actions">
                <button className="btn-secondary" onClick={() => handleTest(provider.id)}>
                  测试连接
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default ModelConfig;

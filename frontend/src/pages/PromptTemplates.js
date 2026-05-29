import React, { useEffect, useState } from 'react';
import api from '../services/api';

function PromptTemplates() {
  const [templates, setTemplates] = useState([]);
  const [selectedRole, setSelectedRole] = useState('');
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [previewResult, setPreviewResult] = useState(null);
  const [newTemplate, setNewTemplate] = useState({
    role: 'planner',
    name: '',
    content: '',
    description: '',
    activate: true,
  });
  const [previewVariables, setPreviewVariables] = useState({});

  const roles = [
    { value: 'planner', label: 'Planner (规划)' },
    { value: 'draft', label: 'Draft (起草)' },
    { value: 'critic', label: 'Critic (审稿)' },
    { value: 'rewrite', label: 'Rewrite (改写)' },
    { value: 'continuity', label: 'Continuity (连续性)' },
    { value: 'learning', label: 'Learning (学习)' },
    { value: 'memory_update', label: 'MemoryUpdate (记忆更新)' },
  ];

  useEffect(() => {
    fetchTemplates();
  }, [selectedRole]);

  const fetchTemplates = async () => {
    setLoading(true);
    try {
      const params = selectedRole ? { role: selectedRole } : {};
      const response = await api.get('/prompts/templates', { params });
      setTemplates(response.data);
    } catch (error) {
      console.error('Error fetching templates:', error);
    }
    setLoading(false);
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await api.post('/prompts/templates', newTemplate);
      setShowCreateModal(false);
      setNewTemplate({
        role: 'planner',
        name: '',
        content: '',
        description: '',
        activate: true,
      });
      fetchTemplates();
    } catch (error) {
      console.error('Error creating template:', error);
    }
  };

  const handleActivate = async (id) => {
    try {
      await api.post(`/prompts/templates/${id}/activate`);
      fetchTemplates();
    } catch (error) {
      console.error('Error activating template:', error);
    }
  };

  const handleDisable = async (id) => {
    try {
      await api.post(`/prompts/templates/${id}/disable`);
      fetchTemplates();
    } catch (error) {
      console.error('Error disabling template:', error);
    }
  };

  const handlePreview = async (template) => {
    // 根据角色生成示例变量
    const exampleVars = {
      planner: {
        chapter_title: '第1章 觉醒',
        chapter_index: 1,
        world_setting: '这是一个修仙世界',
        characters: '[{"name": "主角", "description": "天才少年"}]',
        main_plot: '主角觉醒神秘力量',
        chapter_outline: '[{"title": "觉醒", "summary": "主角觉醒"}]',
        memory_context: '（无）',
        tech_instructions: '无',
        failure_warnings: '无',
        playbook_rules: '无',
        style_boundaries: '无',
        tone_guidelines: '无',
      },
      draft: {
        chapter_title: '第1章 觉醒',
        chapter_index: 1,
        chapter_plan: '{"goal": "展示主角觉醒"}',
        memory_context: '（无）',
        world_setting: '修仙世界',
        characters: '[{"name": "主角"}]',
        style_boundaries: '[]',
        tech_instructions: '无',
        failure_warnings: '无',
        playbook_rules: '无',
        style_boundaries_text: '无',
        tone_guidelines: '无',
        forbidden_items: '[]',
      },
      continuity: {
        chapter_title: '第1章 觉醒',
        chapter_index: 1,
        content_preview: '主角在深夜觉醒...',
        characters: '[{"name": "主角"}]',
        foreshadowing: '[]',
        memory_context: '（无）',
      },
    };

    setPreviewVariables(exampleVars[template.role] || {});
    setShowPreviewModal(true);

    try {
      const response = await api.post('/prompts/render-preview', {
        role: template.role,
        variables: exampleVars[template.role] || {},
      });
      setPreviewResult(response.data);
    } catch (error) {
      console.error('Error previewing template:', error);
      setPreviewResult({ prompt: '预览失败', source: 'error' });
    }
  };

  const getRoleLabel = (roleValue) => {
    const role = roles.find(r => r.value === roleValue);
    return role ? role.label : roleValue;
  };

  if (loading) {
    return <div className="loading">加载中...</div>;
  }

  return (
    <div className="prompt-templates">
      <header className="page-header">
        <h1>Prompt 模板中心</h1>
        <div className="header-actions">
          <select
            value={selectedRole}
            onChange={(e) => setSelectedRole(e.target.value)}
            className="role-filter"
          >
            <option value="">所有角色</option>
            {roles.map(r => (
              <option key={r.value} value={r.value}>{r.label}</option>
            ))}
          </select>
          <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
            + 新建模板
          </button>
        </div>
      </header>

      <div className="templates-list">
        {templates.map((template) => (
          <div key={template.id} className={`template-card ${template.is_active ? 'active' : ''}`}>
            <div className="template-header">
              <span className="role-badge">{getRoleLabel(template.role)}</span>
              <span className="version-badge">v{template.version}</span>
              {template.is_active && <span className="active-badge">活跃</span>}
            </div>
            <h3>{template.name}</h3>
            <p className="description">{template.description || '无描述'}</p>
            <div className="template-meta">
              <span>创建时间: {new Date(template.created_at).toLocaleDateString()}</span>
            </div>
            <div className="template-actions">
              {!template.is_active && (
                <button className="btn-small" onClick={() => handleActivate(template.id)}>
                  激活
                </button>
              )}
              {template.is_active && (
                <button className="btn-small btn-secondary" onClick={() => handleDisable(template.id)}>
                  停用
                </button>
              )}
              <button className="btn-small" onClick={() => handlePreview(template)}>
                预览
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* 创建模态框 */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>新建 Prompt 模板</h2>
            <form onSubmit={handleCreate}>
              <div className="form-group">
                <label>角色</label>
                <select
                  value={newTemplate.role}
                  onChange={(e) => setNewTemplate({ ...newTemplate, role: e.target.value })}
                >
                  {roles.map(r => (
                    <option key={r.value} value={r.value}>{r.label}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>名称</label>
                <input
                  type="text"
                  value={newTemplate.name}
                  onChange={(e) => setNewTemplate({ ...newTemplate, name: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>描述</label>
                <input
                  type="text"
                  value={newTemplate.description}
                  onChange={(e) => setNewTemplate({ ...newTemplate, description: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>模板内容</label>
                <textarea
                  value={newTemplate.content}
                  onChange={(e) => setNewTemplate({ ...newTemplate, content: e.target.value })}
                  rows={15}
                  required
                  placeholder="使用 {变量名} 作为占位符"
                />
              </div>
              <div className="form-group checkbox">
                <label>
                  <input
                    type="checkbox"
                    checked={newTemplate.activate}
                    onChange={(e) => setNewTemplate({ ...newTemplate, activate: e.target.checked })}
                  />
                  立即激活
                </label>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowCreateModal(false)}>
                  取消
                </button>
                <button type="submit" className="btn-primary">创建</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 预览模态框 */}
      {showPreviewModal && (
        <div className="modal-overlay" onClick={() => setShowPreviewModal(false)}>
          <div className="modal modal-large" onClick={(e) => e.stopPropagation()}>
            <h2>模板预览</h2>
            <div className="preview-content">
              <h4>变量:</h4>
              <pre className="variables-preview">{JSON.stringify(previewVariables, null, 2)}</pre>
              <h4>渲染结果:</h4>
              <pre className="prompt-preview">{previewResult?.prompt || '加载中...'}</pre>
              <p className="preview-source">来源: {previewResult?.source || 'unknown'}</p>
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowPreviewModal(false)}>
                关闭
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default PromptTemplates;

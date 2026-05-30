import React, { useState } from 'react';

const ROLES = ['draft', 'critic', 'rewrite', 'continuity'];

function EvolutionPolicyForm({ policy, onSave }) {
  const [form, setForm] = useState({
    role: policy?.role || 'draft',
    enabled: policy?.enabled ?? true,
    min_sample_count: policy?.min_sample_count || 20,
    min_average_score: policy?.min_average_score || 80,
    max_rewrite_rate: policy?.max_rewrite_rate || 0.4,
    trigger_window_days: policy?.trigger_window_days || 7,
    candidate_count: policy?.candidate_count || 3,
    ab_test_sample_count: policy?.ab_test_sample_count || 10,
    min_improvement: policy?.min_improvement || 3.0,
    auto_apply: policy?.auto_apply ?? true,
    rollout_ratio: policy?.rollout_ratio || 0.2,
  });

  const handleChange = (field, value) => {
    setForm(prev => ({ ...prev, [field]: value }));
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <label style={{ fontSize: 13 }}>
          角色
          <select value={form.role} onChange={e => handleChange('role', e.target.value)} style={{ width: '100%', marginTop: 4, padding: 6, borderRadius: 6, border: '1px solid #d0d5dd' }}>
            {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
        </label>
        <label style={{ fontSize: 13 }}>
          启用
          <select value={form.enabled} onChange={e => handleChange('enabled', e.target.value === 'true')} style={{ width: '100%', marginTop: 4, padding: 6, borderRadius: 6, border: '1px solid #d0d5dd' }}>
            <option value="true">是</option>
            <option value="false">否</option>
          </select>
        </label>
        <label style={{ fontSize: 13 }}>
          最小样本数
          <input type="number" value={form.min_sample_count} onChange={e => handleChange('min_sample_count', Number(e.target.value))} style={{ width: '100%', marginTop: 4, padding: 6, borderRadius: 6, border: '1px solid #d0d5dd' }} />
        </label>
        <label style={{ fontSize: 13 }}>
          最低平均分
          <input type="number" value={form.min_average_score} onChange={e => handleChange('min_average_score', Number(e.target.value))} style={{ width: '100%', marginTop: 4, padding: 6, borderRadius: 6, border: '1px solid #d0d5dd' }} />
        </label>
        <label style={{ fontSize: 13 }}>
          最大重写率
          <input type="number" step="0.1" value={form.max_rewrite_rate} onChange={e => handleChange('max_rewrite_rate', Number(e.target.value))} style={{ width: '100%', marginTop: 4, padding: 6, borderRadius: 6, border: '1px solid #d0d5dd' }} />
        </label>
        <label style={{ fontSize: 13 }}>
          候选数
          <input type="number" value={form.candidate_count} onChange={e => handleChange('candidate_count', Number(e.target.value))} style={{ width: '100%', marginTop: 4, padding: 6, borderRadius: 6, border: '1px solid #d0d5dd' }} />
        </label>
      </div>
      {onSave && (
        <button className="btn-primary" onClick={() => onSave(form)} style={{ alignSelf: 'flex-start' }}>
          保存策略
        </button>
      )}
    </div>
  );
}

export default EvolutionPolicyForm;

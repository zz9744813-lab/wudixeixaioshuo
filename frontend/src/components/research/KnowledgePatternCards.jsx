import React from 'react';

function KnowledgePatternCards({ patterns = [], onApply }) {
  if (!patterns.length) {
    return <p style={{ color: '#667085' }}>暂无知识模式。</p>;
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
      {patterns.map(p => (
        <div key={p.id} style={{
          border: '1px solid #e5e7eb', borderRadius: 12, padding: 16, background: '#fff',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <strong>{p.pattern_name}</strong>
            <span style={{
              borderRadius: 999, padding: '2px 8px', fontSize: 11,
              background: '#eef2ff', color: '#3538cd',
            }}>
              {p.pattern_type}
            </span>
          </div>
          <p style={{ margin: '6px 0', fontSize: 12, color: '#667085' }}>
            {p.genre || '通用'} · 置信度: {(p.confidence * 100).toFixed(0)}%
          </p>
          <p style={{ margin: '6px 0', fontSize: 13 }}>{p.description}</p>
          {p.applicable_scene && (
            <p style={{ margin: '4px 0', fontSize: 12, color: '#027a48' }}>
              适用场景: {p.applicable_scene}
            </p>
          )}
          {p.anti_patterns && (
            <p style={{ margin: '4px 0', fontSize: 12, color: '#b42318' }}>
              避坑: {p.anti_patterns}
            </p>
          )}
          {onApply && (
            <button
              style={{ marginTop: 8, padding: '4px 10px', fontSize: 12, border: '1px solid #d0d5dd', borderRadius: 6, background: '#fff', cursor: 'pointer' }}
              onClick={() => onApply(p.id)}
            >
              应用到项目
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

export default KnowledgePatternCards;

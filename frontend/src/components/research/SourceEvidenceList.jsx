import React from 'react';

function SourceEvidenceList({ sources = [] }) {
  if (!sources.length) {
    return <p style={{ color: '#667085' }}>暂无来源记录。</p>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {sources.map(s => (
        <div key={s.id} style={{
          padding: '10px 14px', border: '1px solid #e5e7eb', borderRadius: 10,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <a href={s.url} target="_blank" rel="noopener noreferrer" style={{ fontWeight: 500, textDecoration: 'none' }}>
              {s.title || s.url}
            </a>
            <span style={{
              borderRadius: 999, padding: '2px 8px', fontSize: 11,
              background: '#f2f4f7', color: '#667085',
            }}>
              {s.source_type || 'link'}
            </span>
          </div>
          {s.excerpt && (
            <p style={{ margin: '4px 0 0', fontSize: 12, color: '#667085' }}>
              {s.excerpt}
            </p>
          )}
          <p style={{ margin: '4px 0 0', fontSize: 11, color: '#667085' }}>
            可信度: {(s.trust_score * 100).toFixed(0)}%
          </p>
        </div>
      ))}
    </div>
  );
}

export default SourceEvidenceList;

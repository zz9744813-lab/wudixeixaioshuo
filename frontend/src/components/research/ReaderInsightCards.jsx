import React from 'react';

function ReaderInsightCards({ insights = [] }) {
  if (!insights.length) {
    return <p style={{ color: '#667085' }}>暂无读者洞察。</p>;
  }

  const TYPE_LABELS = { like: '喜欢', dislike: '不喜欢', subscribe: '订阅点', drop: '弃书点' };
  const TYPE_COLORS = { like: '#027a48', dislike: '#b42318', subscribe: '#3538cd', drop: '#b54708' };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
      {insights.map(i => (
        <div key={i.id} style={{
          border: '1px solid #e5e7eb', borderRadius: 12, padding: 16, background: '#fff',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <strong>{i.title}</strong>
            <span style={{
              borderRadius: 999, padding: '2px 8px', fontSize: 11,
              background: `${TYPE_COLORS[i.insight_type] || '#667085'}15`,
              color: TYPE_COLORS[i.insight_type] || '#667085',
            }}>
              {TYPE_LABELS[i.insight_type] || i.insight_type}
            </span>
          </div>
          <p style={{ margin: '6px 0', fontSize: 12, color: '#667085' }}>
            {i.genre || '通用'} · 置信度: {(i.confidence * 100).toFixed(0)}%
          </p>
          <p style={{ margin: '6px 0', fontSize: 13 }}>{i.description}</p>
          {i.evidence && (
            <p style={{ margin: '4px 0', fontSize: 12, color: '#667085' }}>
              证据: {i.evidence}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

export default ReaderInsightCards;

import React from 'react';

function ResearchRunList({ runs = [] }) {
  if (!runs.length) {
    return <p style={{ color: '#667085' }}>暂无研究记录。</p>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {runs.map(run => (
        <div key={run.id} style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
          padding: '10px 14px', border: '1px solid #e5e7eb', borderRadius: 10,
        }}>
          <div>
            <strong>#{run.id} {run.topic}</strong>
            <p style={{ margin: '4px 0 0', fontSize: 12, color: '#667085' }}>
              {run.research_type} · {run.extracted_summary || '处理中...'}
            </p>
          </div>
          <span style={{
            borderRadius: 999, padding: '4px 10px', fontSize: 12,
            background: run.status === 'succeeded' ? '#ecfdf3' : run.status === 'failed' ? '#fef3f2' : '#fffaeb',
            color: run.status === 'succeeded' ? '#027a48' : run.status === 'failed' ? '#b42318' : '#b54708',
          }}>
            {run.status}
          </span>
        </div>
      ))}
    </div>
  );
}

export default ResearchRunList;

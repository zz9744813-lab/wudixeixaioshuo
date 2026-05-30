import React from 'react';

function TrendReportPanel({ reports = [] }) {
  if (!reports.length) {
    return <p style={{ color: '#667085' }}>暂无趋势报告。</p>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {reports.map(r => (
        <div key={r.id} style={{
          border: '1px solid #e5e7eb', borderRadius: 12, padding: 16, background: '#fff',
        }}>
          <strong>{r.report_title}</strong>
          <p style={{ margin: '4px 0', fontSize: 12, color: '#667085' }}>
            {r.genre || '通用'} · {r.platform || '综合'}
          </p>
          <p style={{ margin: '6px 0', fontSize: 13 }}>{r.report_body}</p>
          {r.trend_tags && r.trend_tags.length > 0 && (
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
              {r.trend_tags.map((tag, i) => (
                <span key={i} style={{
                  borderRadius: 999, padding: '2px 8px', fontSize: 11,
                  background: '#eef2ff', color: '#3538cd',
                }}>
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export default TrendReportPanel;

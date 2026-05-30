import React from 'react';

const STATUS_COLORS = {
  pending: { bg: '#f2f4f7', color: '#667085' },
  diagnosing: { bg: '#fffaeb', color: '#b54708' },
  proposing: { bg: '#fffaeb', color: '#b54708' },
  testing: { bg: '#fffaeb', color: '#b54708' },
  applied: { bg: '#ecfdf3', color: '#027a48' },
  rolled_back: { bg: '#fef3f2', color: '#b42318' },
  failed: { bg: '#fef3f2', color: '#b42318' },
};

function EvolutionRunTimeline({ runs = [] }) {
  if (!runs.length) {
    return <p style={{ color: '#667085' }}>暂无进化运行记录。</p>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {runs.map(r => {
        const style = STATUS_COLORS[r.status] || STATUS_COLORS.pending;
        return (
          <div key={r.id} style={{
            padding: '12px 16px', border: '1px solid #e5e7eb', borderRadius: 10,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong>#{r.id} {r.role}</strong>
                <span style={{ marginLeft: 8, fontSize: 12, color: '#667085' }}>
                  {r.created_at && new Date(r.created_at).toLocaleString()}
                </span>
              </div>
              <span style={{
                borderRadius: 999, padding: '4px 10px', fontSize: 12,
                background: style.bg, color: style.color,
              }}>
                {r.status}
              </span>
            </div>
            {r.diagnosis && (
              <p style={{ margin: '6px 0 0', fontSize: 12 }}>诊断: {r.diagnosis}</p>
            )}
            {r.candidate_prompts_json && (
              <p style={{ margin: '4px 0 0', fontSize: 12, color: '#3538cd' }}>
                候选数: {r.candidate_prompts_json.length}
              </p>
            )}
            {r.ab_test_result_json && (
              <p style={{ margin: '4px 0 0', fontSize: 12, color: '#027a48' }}>
                改进幅度: {r.ab_test_result_json.improvement?.toFixed(1) || 'N/A'}
              </p>
            )}
            {r.error_message && (
              <p style={{ margin: '4px 0 0', fontSize: 12, color: '#b42318' }}>{r.error_message}</p>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default EvolutionRunTimeline;

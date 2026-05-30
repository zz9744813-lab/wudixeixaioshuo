import React from 'react';

const STATUS_COLORS = {
  pending: { bg: '#f2f4f7', color: '#667085' },
  running: { bg: '#fffaeb', color: '#b54708' },
  succeeded: { bg: '#ecfdf3', color: '#027a48' },
  failed: { bg: '#fef3f2', color: '#b42318' },
  skipped: { bg: '#f2f4f7', color: '#667085' },
};

function AgentStepTimeline({ steps = [] }) {
  if (!steps.length) {
    return <p style={{ color: '#667085' }}>暂无步骤记录。</p>;
  }

  return (
    <div style={{ position: 'relative', paddingLeft: 24 }}>
      <div style={{
        position: 'absolute', left: 8, top: 0, bottom: 0,
        width: 2, background: '#e5e7eb',
      }} />
      {steps.map((step, idx) => {
        const style = STATUS_COLORS[step.status] || STATUS_COLORS.pending;
        return (
          <div key={step.id || idx} style={{
            position: 'relative', marginBottom: 16, paddingLeft: 16,
          }}>
            <div style={{
              position: 'absolute', left: -4, top: 6,
              width: 10, height: 10, borderRadius: '50%',
              background: style.color, border: '2px solid #fff',
            }} />
            <div style={{
              padding: '10px 14px', border: '1px solid #e5e7eb',
              borderRadius: 10, background: '#fff',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <strong>{step.title}</strong>
                <span style={{
                  borderRadius: 999, padding: '2px 8px', fontSize: 11,
                  background: style.bg, color: style.color,
                }}>
                  {step.status}
                </span>
              </div>
              <p style={{ margin: '4px 0 0', fontSize: 12, color: '#667085' }}>
                {step.tool_name} · 尝试 {step.attempt_count || 0} 次
              </p>
              {step.started_at && (
                <p style={{ margin: '2px 0 0', fontSize: 11, color: '#667085' }}>
                  {new Date(step.started_at).toLocaleTimeString()} — {step.finished_at ? new Date(step.finished_at).toLocaleTimeString() : '进行中'}
                </p>
              )}
              {step.error_message && (
                <p style={{ margin: '4px 0 0', fontSize: 12, color: '#b42318' }}>
                  {step.error_message}
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default AgentStepTimeline;

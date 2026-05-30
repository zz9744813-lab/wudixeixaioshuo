import React from 'react';

const STATUS_COLORS = {
  pending: { bg: '#f2f4f7', color: '#667085' },
  running: { bg: '#fffaeb', color: '#b54708' },
  succeeded: { bg: '#ecfdf3', color: '#027a48' },
  failed: { bg: '#fef3f2', color: '#b42318' },
  skipped: { bg: '#f2f4f7', color: '#667085' },
};

function PlanDagView({ steps = [] }) {
  if (!steps.length) {
    return <p style={{ color: '#667085' }}>暂无计划步骤。</p>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {steps.map((step, idx) => {
        const style = STATUS_COLORS[step.status] || STATUS_COLORS.pending;
        return (
          <div key={step.id || idx} style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '10px 14px', border: '1px solid #e5e7eb', borderRadius: 10,
          }}>
            <div>
              <strong>{step.title}</strong>
              <p style={{ margin: '4px 0 0', fontSize: 12, color: '#667085' }}>
                {step.step_key} · {step.tool_name}
                {step.depends_on?.length > 0 && ` ← [${step.depends_on.join(', ')}]`}
              </p>
              {step.error_message && (
                <p style={{ margin: '4px 0 0', fontSize: 12, color: '#b42318' }}>
                  {step.error_message}
                </p>
              )}
            </div>
            <span style={{
              borderRadius: 999, padding: '4px 10px', fontSize: 12,
              background: style.bg, color: style.color, whiteSpace: 'nowrap',
            }}>
              {step.status}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default PlanDagView;

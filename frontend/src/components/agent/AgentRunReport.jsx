import React from 'react';

function AgentRunReport({ report }) {
  if (!report) {
    return <p style={{ color: '#667085' }}>尚未生成最终报告。</p>;
  }

  const data = typeof report === 'string' ? (() => { try { return JSON.parse(report); } catch { return { text: report }; } })() : report;

  return (
    <div style={{ background: '#f8fafc', borderRadius: 12, padding: 20 }}>
      {data.title && <h3 style={{ marginTop: 0 }}>{data.title}</h3>}
      {data.user_request && (
        <div style={{ marginBottom: 12 }}>
          <strong>用户需求：</strong>
          <p style={{ margin: '4px 0 0' }}>{data.user_request}</p>
        </div>
      )}
      {data.project_id && (
        <p><strong>项目 ID：</strong>{data.project_id}</p>
      )}
      {data.key_decisions && (
        <div style={{ marginBottom: 12 }}>
          <strong>关键决策：</strong>
          <ul style={{ margin: '4px 0 0', paddingLeft: 20 }}>
            {data.key_decisions.map((d, i) => <li key={i}>{d}</li>)}
          </ul>
        </div>
      )}
      {data.steps_summary && (
        <div style={{ marginBottom: 12 }}>
          <strong>步骤汇总：</strong>
          <p style={{ margin: '4px 0 0' }}>
            总计 {data.steps_summary.total} 步 ·
            成功 {data.steps_summary.succeeded} ·
            失败 {data.steps_summary.failed} ·
            跳过 {data.steps_summary.skipped}
          </p>
        </div>
      )}
      {data.cost_summary && (
        <div style={{ marginBottom: 12 }}>
          <strong>费用汇总：</strong>
          <p style={{ margin: '4px 0 0' }}>
            Token: {data.cost_summary.total_tokens?.toLocaleString() || 0} ·
            费用: ${data.cost_summary.total_cost?.toFixed(4) || '0.00'}
          </p>
        </div>
      )}
      {data.risks && (
        <div>
          <strong>风险提示：</strong>
          <ul style={{ margin: '4px 0 0', paddingLeft: 20 }}>
            {data.risks.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        </div>
      )}
      {!data.title && !data.user_request && data.text && (
        <pre style={{ margin: 0 }}>{data.text}</pre>
      )}
    </div>
  );
}

export default AgentRunReport;

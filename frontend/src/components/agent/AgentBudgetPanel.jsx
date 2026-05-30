import React from 'react';

function AgentBudgetPanel({ run }) {
  if (!run) return null;

  const tokensUsed = run.used_tokens || 0;
  const tokensBudget = run.budget_tokens;
  const costUsed = run.used_cost || 0;
  const costBudget = run.budget_cost;
  const stepsExecuted = (run.steps || []).length;
  const maxSteps = run.max_steps || 30;

  const tokenPct = tokensBudget ? Math.min(100, (tokensUsed / tokensBudget) * 100) : 0;
  const costPct = costBudget ? Math.min(100, (costUsed / costBudget) * 100) : 0;
  const stepPct = Math.min(100, (stepsExecuted / maxSteps) * 100);

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
      <MetricCard label="预算 Token" value={tokensBudget ? tokensBudget.toLocaleString() : '∞'} sub={`${tokensUsed.toLocaleString()} 已用`} pct={tokenPct} />
      <MetricCard label="预算费用" value={costBudget ? `$${costBudget.toFixed(2)}` : '∞'} sub={`$${costUsed.toFixed(4)} 已用`} pct={costPct} />
      <MetricCard label="最大步骤" value={maxSteps} sub={`${stepsExecuted} 已执行`} pct={stepPct} />
      <MetricCard label="最大并发" value={run.max_concurrency || 3} sub="" pct={0} />
    </div>
  );
}

function MetricCard({ label, value, sub, pct }) {
  return (
    <div style={{
      background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12,
      padding: 16, boxShadow: '0 1px 2px rgba(16,24,40,0.06)',
    }}>
      <p style={{ margin: 0, color: '#667085', fontSize: 13 }}>{label}</p>
      <p style={{ margin: '8px 0 4px', fontSize: 24, fontWeight: 700 }}>{value}</p>
      {sub && <p style={{ margin: 0, fontSize: 12, color: '#667085' }}>{sub}</p>}
      {pct > 0 && (
        <div style={{ marginTop: 8, height: 4, background: '#f2f4f7', borderRadius: 2, overflow: 'hidden' }}>
          <div style={{
            height: '100%', borderRadius: 2,
            width: `${pct}%`,
            background: pct > 80 ? '#b42318' : pct > 50 ? '#b54708' : '#027a48',
          }} />
        </div>
      )}
    </div>
  );
}

export default AgentBudgetPanel;

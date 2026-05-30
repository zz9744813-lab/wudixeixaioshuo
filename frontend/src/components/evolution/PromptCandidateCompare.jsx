import React from 'react';

function PromptCandidateCompare({ candidates = [] }) {
  if (!candidates.length) {
    return <p style={{ color: '#667085' }}>暂无候选 Prompt。</p>;
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: `repeat(${Math.min(candidates.length, 3)}, 1fr)`, gap: 12 }}>
      {candidates.map((c, idx) => (
        <div key={idx} style={{
          border: '1px solid #e5e7eb', borderRadius: 12, padding: 16, background: '#fff',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <strong>候选 {idx + 1}</strong>
            <span style={{
              borderRadius: 999, padding: '2px 8px', fontSize: 11,
              background: '#eef2ff', color: '#3538cd',
            }}>
              #{idx + 1}
            </span>
          </div>
          {c.modifications && (
            <div style={{ marginBottom: 8 }}>
              <p style={{ margin: 0, fontSize: 12, fontWeight: 600 }}>修改说明：</p>
              <p style={{ margin: '4px 0 0', fontSize: 12 }}>{c.modifications}</p>
            </div>
          )}
          {c.expected_improvement && (
            <div style={{ marginBottom: 8 }}>
              <p style={{ margin: 0, fontSize: 12, fontWeight: 600 }}>预期改善：</p>
              <p style={{ margin: '4px 0 0', fontSize: 12, color: '#027a48' }}>{c.expected_improvement}</p>
            </div>
          )}
          {c.risks && (
            <div style={{ marginBottom: 8 }}>
              <p style={{ margin: 0, fontSize: 12, fontWeight: 600 }}>风险：</p>
              <p style={{ margin: '4px 0 0', fontSize: 12, color: '#b42318' }}>{c.risks}</p>
            </div>
          )}
          {c.prompt && (
            <details>
              <summary style={{ fontSize: 12, cursor: 'pointer', color: '#667085' }}>查看完整 Prompt</summary>
              <pre style={{ marginTop: 8, fontSize: 11, maxHeight: 200, overflow: 'auto' }}>{c.prompt}</pre>
            </details>
          )}
        </div>
      ))}
    </div>
  );
}

export default PromptCandidateCompare;

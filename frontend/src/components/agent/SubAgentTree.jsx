import React from 'react';

const STATUS_COLORS = {
  pending: { bg: '#f2f4f7', color: '#667085' },
  running: { bg: '#fffaeb', color: '#b54708' },
  succeeded: { bg: '#ecfdf3', color: '#027a48' },
  failed: { bg: '#fef3f2', color: '#b42318' },
  cancelled: { bg: '#fef3f2', color: '#b42318' },
};

function SubAgentTree({ tasksByParent = {} }) {
  const parentKeys = Object.keys(tasksByParent);

  if (!parentKeys.length) {
    return <p style={{ color: '#667085' }}>暂无子 Agent 任务。</p>;
  }

  return (
    <div style={{ fontFamily: 'monospace' }}>
      {parentKeys.map(parentKey => (
        <div key={parentKey} style={{ marginBottom: 16 }}>
          <div style={{ fontWeight: 600, marginBottom: 8, color: '#667085' }}>
            {parentKey === 'root' ? '根任务' : `步骤 ${parentKey}`}
          </div>
          {tasksByParent[parentKey].map((task, idx) => {
            const style = STATUS_COLORS[task.status] || STATUS_COLORS.pending;
            const isLast = idx === tasksByParent[parentKey].length - 1;
            return (
              <div key={task.id} style={{
                display: 'flex', alignItems: 'flex-start', gap: 8,
                paddingLeft: 16, marginBottom: 4,
              }}>
                <span style={{ color: '#d0d5dd', userSelect: 'none' }}>
                  {isLast ? '└─' : '├─'}
                </span>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 500 }}>{task.title}</span>
                    <span style={{
                      borderRadius: 999, padding: '2px 8px', fontSize: 11,
                      background: style.bg, color: style.color,
                    }}>
                      {task.status}
                    </span>
                  </div>
                  <p style={{ margin: '2px 0 0', fontSize: 12, color: '#667085' }}>
                    {task.role} · {task.task_type} · {task.provider_name || 'local'} / {task.model_name || 'rule-based'}
                    {task.token_count > 0 && ` · ${task.token_count} tokens`}
                    {task.cost > 0 && ` · $${task.cost.toFixed(4)}`}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}

export default SubAgentTree;

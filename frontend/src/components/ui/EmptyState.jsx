import React from 'react';
import { Inbox } from 'lucide-react';
import '../../styles/primitives.css';

/**
 * EmptyState 空状态组件
 * @param {string} title - 标题
 * @param {string} hint - 提示文字
 * @param {ReactNode} icon - 自定义图标
 * @param {ReactNode} action - 操作按钮
 */
export function EmptyState({
  title = '暂无数据',
  hint = '',
  icon,
  action,
  className = '',
  ...props
}) {
  return (
    <div className={`empty-state ${className}`} {...props}>
      {icon || <Inbox size={48} style={{ opacity: 0.4, marginBottom: '16px' }} />}
      <h3 className="empty-state__title">{title}</h3>
      {hint && <p className="empty-state__hint">{hint}</p>}
      {action && <div style={{ marginTop: '20px' }}>{action}</div>}
    </div>
  );
}

export default EmptyState;

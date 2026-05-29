import React from 'react';
import { AlertCircle } from 'lucide-react';
import { Button } from './Button';
import '../../styles/primitives.css';

/**
 * ErrorState 错误状态组件
 * @param {string} message - 错误信息
 * @param {function} onRetry - 重试回调
 * @param {string} className
 */
export function ErrorState({
  message = '加载失败，请重试',
  onRetry,
  className = '',
  ...props
}) {
  return (
    <div className={`error-state ${className}`} {...props}>
      <AlertCircle size={48} style={{ marginBottom: '16px', opacity: 0.6 }} />
      <p className="error-state__message">{message}</p>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          重新加载
        </Button>
      )}
    </div>
  );
}

export default ErrorState;

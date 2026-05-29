import React from 'react';
import { Skeleton } from './Skeleton';
import { EmptyState } from './EmptyState';
import { ErrorState } from './ErrorState';

/**
 * AsyncState 异步状态组件
 * 统一处理加载、错误、空数据、正常内容四种状态
 *
 * @param {boolean} loading - 加载中
 * @param {string} error - 错误信息
 * @param {boolean} isEmpty - 是否空数据
 * @param {function} onRetry - 重试回调
 * @param {ReactNode} skeleton - 自定义骨架屏
 * @param {string} emptyTitle - 空状态标题
 * @param {string} emptyHint - 空状态提示
 * @param {ReactNode} children - 正常内容
 */
export function AsyncState({
  loading,
  error,
  isEmpty,
  onRetry,
  skeleton,
  emptyTitle = '暂无数据',
  emptyHint = '',
  children,
}) {
  if (loading) {
    return skeleton || <Skeleton rows={4} />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={onRetry} />;
  }

  if (isEmpty) {
    return <EmptyState title={emptyTitle} hint={emptyHint} />;
  }

  return children;
}

export default AsyncState;

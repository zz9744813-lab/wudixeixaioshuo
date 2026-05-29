import React from 'react';
import '../../styles/primitives.css';

/**
 * Skeleton 骨架屏组件
 * @param {number} rows - 行数
 * @param {number} height - 单行高度(px)
 * @param {string} className
 */
export function Skeleton({
  rows = 4,
  height = 20,
  className = '',
  ...props
}) {
  return (
    <div className={`skeleton-container ${className}`} {...props}>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="skeleton"
          style={{
            height: `${height}px`,
            marginBottom: i < rows - 1 ? '12px' : 0,
            borderRadius: '4px',
          }}
        />
      ))}
    </div>
  );
}

export default Skeleton;

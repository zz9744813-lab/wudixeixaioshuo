import React from 'react';
import '../../styles/primitives.css';

/**
 * Card 组件
 * @param {boolean} hover - 是否启用悬停效果
 * @param {ReactNode} children
 * @param {string} className
 */
export function Card({
  hover = false,
  children,
  className = '',
  ...props
}) {
  const hoverClass = hover ? 'card--hover' : '';

  return (
    <div className={`card ${hoverClass} ${className}`} {...props}>
      {children}
    </div>
  );
}

export default Card;

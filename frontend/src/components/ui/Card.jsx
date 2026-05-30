import React from 'react';
import '../../styles/primitives.css';

/**
 * Card 组件（控制台风格）
 */
export function Card({
  hover = false,
  children,
  className = '',
  active = false,
  ...props
}) {
  const hoverClass = hover ? 'card--hover' : '';
  const activeClass = active ? 'panel--active' : '';

  return (
    <div className={`panel card ${hoverClass} ${activeClass} ${className}`} {...props}>
      {children}
    </div>
  );
}

export default Card;
import React from 'react';
import '../../styles/primitives.css';

/**
 * Badge 组件
 * @param {string} variant - accent | success | warning | danger | muted
 * @param {ReactNode} children
 * @param {string} className
 */
export function Badge({
  variant = 'muted',
  children,
  className = '',
  ...props
}) {
  const variantClass = `badge--${variant}`;

  return (
    <span className={`badge ${variantClass} ${className}`} {...props}>
      {children}
    </span>
  );
}

export default Badge;

import React from 'react';
import '../../styles/primitives.css';

/**
 * Button 组件
 * @param {string} variant - primary | secondary | danger | ghost
 * @param {string} size - sm | md
 * @param {boolean} disabled
 * @param {function} onClick
 * @param {ReactNode} children
 * @param {string} className
 */
export function Button({
  variant = 'primary',
  size = 'md',
  disabled = false,
  onClick,
  children,
  className = '',
  type = 'button',
  ...props
}) {
  const variantClass = `btn--${variant}`;
  const sizeClass = size === 'sm' ? 'btn--sm' : '';

  return (
    <button
      type={type}
      className={`btn ${variantClass} ${sizeClass} ${className}`}
      disabled={disabled}
      onClick={onClick}
      {...props}
    >
      {children}
    </button>
  );
}

export default Button;

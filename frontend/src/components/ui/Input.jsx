import React from 'react';
import '../../styles/primitives.css';

/**
 * Input 组件
 * @param {string} className
 */
export function Input({ className = '', ...props }) {
  return <input className={`input ${className}`} {...props} />;
}

export default Input;

/**
 * Input - 通用输入框组件
 *
 * 风格与表单 <input> 一致，支持 password 类型。
 * P7 build-fix: ApiKeyModal.js 引用此组件，但原项目未实现。
 */
import React from 'react';

export function Input({
  type = 'text',
  value = '',
  onChange,
  placeholder = '',
  disabled = false,
  ...rest
}) {
  return (
    <input
      type={type}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      disabled={disabled}
      style={{
        background: 'var(--bg-sunken, #1a1f2e)',
        color: 'var(--text, #e4e6eb)',
        border: '1px solid var(--border, #2a3142)',
        borderRadius: 'var(--r-sm, 6px)',
        padding: '6px 10px',
        fontSize: 'var(--fs-sm, 13px)',
        width: '100%',
        boxSizing: 'border-box',
      }}
      {...rest}
    />
  );
}

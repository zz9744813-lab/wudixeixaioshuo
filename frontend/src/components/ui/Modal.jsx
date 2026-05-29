import React, { useEffect, useRef } from 'react';
import '../../styles/primitives.css';

/**
 * Modal 组件
 * 支持: role="dialog", aria-modal="true", Esc关闭, 点击遮罩关闭, 锁定body滚动, 焦点归还
 *
 * @param {boolean} open - 是否打开
 * @param {function} onClose - 关闭回调
 * @param {string} title - 标题
 * @param {ReactNode} children - 内容
 * @param {ReactNode} footer - 底部操作区
 * @param {string} size - sm | md | lg | xl
 */
export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
  size = 'md',
  ...props
}) {
  const modalRef = useRef(null);
  const previousActiveElement = useRef(null);

  useEffect(() => {
    if (open) {
      // 保存之前聚焦的元素
      previousActiveElement.current = document.activeElement;

      // 锁定 body 滚动
      document.body.style.overflow = 'hidden';

      // 聚焦到模态框
      setTimeout(() => {
        modalRef.current?.focus();
      }, 0);

      // 监听 Esc 键
      const handleKeyDown = (e) => {
        if (e.key === 'Escape') {
          onClose();
        }
      };

      document.addEventListener('keydown', handleKeyDown);

      return () => {
        document.removeEventListener('keydown', handleKeyDown);
      };
    } else {
      // 恢复 body 滚动
      document.body.style.overflow = '';

      // 归还焦点
      if (previousActiveElement.current) {
        previousActiveElement.current.focus?.();
      }
    }
  }, [open, onClose]);

  // 清理函数
  useEffect(() => {
    return () => {
      document.body.style.overflow = '';
    };
  }, []);

  if (!open) return null;

  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div
      className="modal__overlay"
      onClick={handleOverlayClick}
      role="presentation"
    >
      <div
        ref={modalRef}
        className={`modal modal--${size}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? 'modal-title' : undefined}
        tabIndex={-1}
        {...props}
      >
        {title && (
          <div className="modal__header">
            <h2 id="modal-title" className="modal__title">
              {title}
            </h2>
          </div>
        )}
        <div className="modal__body">{children}</div>
        {footer && <div className="modal__footer">{footer}</div>}
      </div>
    </div>
  );
}

export default Modal;

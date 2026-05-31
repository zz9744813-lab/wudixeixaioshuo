import React from 'react';
import { Modal } from './Modal';

export default function ConfirmModal({ state, onOk, onCancel }) {
  const { open, title, message } = state;
  return (
    <Modal open={open} onClose={onCancel} title={title}>
      <div className={styles.body}>
        <p className={styles.message}>{message}</p>
      </div>
      <div className={styles.actions}>
        <button type="button" className={styles.cancel} onClick={onCancel}>取消</button>
        <button type="button" className={styles.ok} onClick={onOk}>确认执行</button>
      </div>
    </Modal>
  );
}

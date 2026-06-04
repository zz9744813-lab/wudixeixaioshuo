/**
 * AutoAssignModal - 一键自动分配弹窗
 *
 * 流程:
 * 1. 调 dry_run=true 拿到所有 agent 的预览
 * 2. 用户确认 → 调 dry_run=false 真正落库
 * 3. 完成后回到列表自动刷新
 */
import React, { useCallback, useEffect, useState } from 'react';
import api from '../../services/api';
import { toArray } from '../../utils/nullSafety';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { useConfirm } from '../../hooks/useConfirm';
import ConfirmModal from '../ConfirmModal';
import styles from './AgentMatrix.module.css';

export default function AutoAssignModal({ onClose, onCompleted, onToast }) {
  const [preview, setPreview] = useState(null);
  const [includeLocked, setIncludeLocked] = useState(false);
  const [applying, setApplying] = useState(false);
  const { confirm, state: confirmState, handleOk, handleCancel } = useConfirm();

  const runPreview = useCallback(async () => {
    try {
      const res = await api.post('/agent-model-configs/auto-assign', {
        dry_run: true,
        include_manual_locked: includeLocked,
      });
      setPreview(res.data);
    } catch (err) {
      onToast?.(`预览失败: ${err?.message || ''}`, 'danger');
    }
  }, [includeLocked, onToast]);

  useEffect(() => { runPreview(); }, [runPreview]);

  const handleApply = async () => {
    const summary = preview
      ? `${preview.results?.length || 0} 个 agent · ${preview.results?.filter((r) => r.status === 'updated' || r.status === 'would_update').length || 0} 个会被改`
      : '';
    const ok = await confirm({
      title: '确认应用自动分配',
      message: '将根据 dry-run 结果落库' + (summary ? '：' + summary : '') + '。' +
        (includeLocked ? '【注意】会覆盖手动锁定的 agent。' : '手动锁定的 agent 不会被覆盖。'),
      confirmText: '确认应用',
      cancelText: '取消',
    });
    if (!ok) return;

    setApplying(true);
    try {
      const res = await api.post('/agent-model-configs/auto-assign', {
        dry_run: false,
        include_manual_locked: includeLocked,
      });
      onToast?.(`已应用 ${res.data.updated} 个 / 跳过 ${res.data.skipped_locked} 个手动锁定`, 'success');
      onCompleted?.();
    } catch (err) {
      onToast?.(`应用失败: ${err?.message || ''}`, 'danger');
    } finally {
      setApplying(false);
    }
  };

  const results = toArray(preview?.results);
  const wouldUpdate = results.filter((r) => r.status === 'updated' || r.status === 'would_update').length;
  const noCandidate = results.filter((r) => r.status === 'no_candidate').length;

  return (
    <Modal
      open
      onClose={onClose}
      title="一键自动分配"
      size="md"
      footer={
        <div style={{ display: 'flex', gap: 8, justifyContent: 'space-between', width: '100%' }}>
          <Button variant="secondary" size="sm" onClick={onClose}>关闭</Button>
          <div style={{ display: 'flex', gap: 8 }}>
            <Button variant="ghost" size="sm" onClick={runPreview}>重新预览</Button>
            <Button variant="primary" onClick={handleApply} disabled={applying || !preview || wouldUpdate === 0}>
              {applying ? '应用中…' : `确认应用 (${wouldUpdate})`}
            </Button>
          </div>
        </div>
      }
    >
      {!preview ? (
        <div className={styles.empty}>加载预览中…</div>
      ) : (
        <>
          <div className={styles.advancedOptions}>
            <label className={styles.checkboxLabel}>
              <input
                type="checkbox"
                checked={includeLocked}
                onChange={(e) => setIncludeLocked(e.target.checked)}
              />
              <span>同时覆盖手动锁定的 Agent</span>
            </label>
            <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-muted)' }}>
              默认只改 auto 模式的 agent
            </span>
          </div>

          <div className={styles.summaryBar} style={{ marginBottom: 12 }}>
            <div className={styles.summaryCell}>
              <span>总 Agent</span>
              <strong>{results.length}</strong>
            </div>
            <div className={styles.summaryCell}>
              <span>将被更新</span>
              <strong className={styles.success}>{wouldUpdate}</strong>
            </div>
            <div className={styles.summaryCell}>
              <span>无候选</span>
              <strong className={noCandidate > 0 ? styles.danger : ''}>{noCandidate}</strong>
            </div>
          </div>

          {results.length === 0 ? (
            <div className={styles.empty}>没有 agent 可被自动分配</div>
          ) : (
            <div className={styles.previewList}>
              {results.map((r) => (
                <PreviewItem key={r.role} item={r} />
              ))}
            </div>
          )}
        </>
      )}

      <ConfirmModal state={confirmState} onOk={handleOk} onCancel={handleCancel} />
    </Modal>
  );
}


function PreviewItem({ item }) {
  const isUpdate = item.status === 'updated' || item.status === 'would_update';
  return (
    <div className={styles.previewItem}>
      <span className={styles.role}>{item.role}</span>
      {isUpdate ? (
        <>
          <span className={styles.target}>
            → {item.selected_provider} / {item.selected_model}
          </span>
          <span className={styles.score}>score {item.score}</span>
        </>
      ) : item.status === 'no_candidate' ? (
        <>
          <span className={styles.target} style={{ color: 'var(--text-muted)' }}>
            暂无可用候选
          </span>
          <span className={styles.noCandidate}>—</span>
        </>
      ) : (
        <>
          <span className={styles.target}>
            {item.status}
          </span>
          <span>—</span>
        </>
      )}
    </div>
  );
}

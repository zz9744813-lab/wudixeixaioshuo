import React, { useState, useEffect } from 'react';
import Modal from './ui/Modal';
import { Button } from './ui/Button';
import { Input } from './ui/Input';

function ApiKeyModal({ isOpen, onClose }) {
  const [apiKey, setApiKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [savedMsg, setSavedMsg] = useState('');

  useEffect(() => {
    if (isOpen) {
      const savedKey = localStorage.getItem('APP_API_KEY') || '';
      setApiKey(savedKey);
      setShowKey(false);
      setSavedMsg('');
    }
  }, [isOpen]);

  const handleSave = () => {
    if (!apiKey.trim()) return;
    const prev = localStorage.getItem('APP_API_KEY') || '';
    localStorage.setItem('APP_API_KEY', apiKey.trim());
    setSavedMsg(prev ? '已更新' : '已保存');
    setTimeout(() => {
      setSavedMsg('');
      onClose(true);
    }, 600);
  };

  const handleClear = () => {
    localStorage.removeItem('APP_API_KEY');
    setApiKey('');
    setSavedMsg('已清除');
    setTimeout(() => {
      setSavedMsg('');
      onClose(true);
    }, 600);
  };

  const masked = apiKey.trim() ? apiKey.trim().slice(0, 8) + '••••••••' : '';

  return (
    <Modal
      open={isOpen}
      onClose={() => onClose(false)}
      title="设置 API Key"
      footer={
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <Button variant="secondary" onClick={() => onClose(false)}>关闭</Button>
          {apiKey.trim() && (
            <Button variant="danger" onClick={handleClear}>清除</Button>
          )}
          <Button variant="primary" onClick={handleSave} disabled={!apiKey.trim()}>
            {savedMsg || '保存'}
          </Button>
        </div>
      }
    >
      <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--fs-sm)', marginBottom: 16 }}>
        请输入后端 API Key 以访问服务。Key 将存储在浏览器本地。
      </p>
      <label>
        <span>API Key</span>
        <Input
          type={showKey ? 'text' : 'password'}
          value={apiKey}
          onChange={(e) => { setApiKey(e.target.value); setSavedMsg(''); }}
          placeholder="输入您的 API Key"
        />
      </label>
      {masked && (
        <p style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-muted)', marginTop: 6 }}>
          当前：{masked}
        </p>
      )}
      <label style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 12 }}>
        <input
          type="checkbox"
          checked={showKey}
          onChange={(e) => setShowKey(e.target.checked)}
        />
        <span style={{ fontSize: 'var(--fs-sm)', color: 'var(--text-secondary)' }}>
          显示完整 Key
        </span>
      </label>
      <p style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-muted)', marginTop: 16 }}>
        也可在浏览器控制台执行：
        <code style={{ background: 'var(--bg-sunken)', padding: '2px 6px', borderRadius: 4, fontSize: 11, marginLeft: 4 }}>
          localStorage.setItem('APP_API_KEY', 'your-key')
        </code>
      </p>
    </Modal>
  );
}

export default ApiKeyModal;

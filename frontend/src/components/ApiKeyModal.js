import React, { useState, useEffect } from 'react';
import './ApiKeyModal.css';

function ApiKeyModal({ isOpen, onClose }) {
  const [apiKey, setApiKey] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    // 加载已保存的 API Key
    const savedKey = localStorage.getItem('APP_API_KEY') || '';
    setApiKey(savedKey);
  }, []);

  const handleSave = () => {
    if (apiKey.trim()) {
      localStorage.setItem('APP_API_KEY', apiKey.trim());
      setSaved(true);
      setTimeout(() => {
        setSaved(false);
        onClose();
        window.location.reload(); // 刷新以应用新 Key
      }, 1000);
    }
  };

  const handleClear = () => {
    localStorage.removeItem('APP_API_KEY');
    setApiKey('');
    setSaved(true);
    setTimeout(() => {
      setSaved(false);
      onClose();
      window.location.reload();
    }, 1000);
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <h2>设置 API Key</h2>
        <p className="modal-description">
          请输入后端 API Key 以访问服务。如果没有 Key，请联系管理员或查看 .env 文件中的 APP_API_KEY。
        </p>

        <div className="form-group">
          <label>API Key:</label>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="输入您的 API Key"
            className="api-key-input"
          />
        </div>

        {saved && (
          <div className="success-message">
            ✅ 已保存！页面即将刷新...
          </div>
        )}

        <div className="modal-actions">
          <button onClick={handleSave} className="btn-primary">
            保存
          </button>
          {apiKey && (
            <button onClick={handleClear} className="btn-danger">
              清除
            </button>
          )}
          <button onClick={onClose} className="btn-secondary">
            取消
          </button>
        </div>

        <div className="help-text">
          <p>💡 提示：也可以在浏览器控制台执行：</p>
          <code>localStorage.setItem('APP_API_KEY', 'your-key')</code>
        </div>
      </div>
    </div>
  );
}

export default ApiKeyModal;

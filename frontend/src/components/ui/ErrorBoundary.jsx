import React from 'react';
import { Button } from './Button';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
    };
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error, errorInfo) {
    console.error('页面运行时异常：', error, errorInfo);
  }

  handleReload = () => {
    window.location.reload();
  };

  handleHome = () => {
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: '#0f172a',
            color: '#e5e7eb',
            padding: 24,
          }}
        >
          <div
            style={{
              maxWidth: 720,
              width: '100%',
              border: '1px solid rgba(148, 163, 184, 0.25)',
              borderRadius: 16,
              background: 'rgba(15, 23, 42, 0.92)',
              padding: 28,
              boxShadow: '0 24px 80px rgba(0,0,0,0.35)',
            }}
          >
            <h1 style={{ margin: '0 0 12px', fontSize: 24 }}>页面出现异常</h1>
            <p
              style={{
                margin: '0 0 18px',
                color: '#94a3b8',
                lineHeight: 1.7,
              }}
            >
              当前页面发生运行时错误，但系统没有崩溃。请刷新页面或返回首页。
            </p>
            <pre
              style={{
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                background: 'rgba(2, 6, 23, 0.7)',
                border: '1px solid rgba(148, 163, 184, 0.18)',
                borderRadius: 12,
                padding: 14,
                color: '#fca5a5',
                maxHeight: 220,
                overflow: 'auto',
              }}
            >
              {this.state.error?.message || '未知错误'}
            </pre>
            <div style={{ display: 'flex', gap: 12, marginTop: 18 }}>
              <Button variant="primary" onClick={this.handleReload}>
                刷新页面
              </Button>
              <Button variant="secondary" onClick={this.handleHome}>
                返回首页
              </Button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;

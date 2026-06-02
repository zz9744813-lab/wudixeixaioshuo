import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from './ui/Button';
import PageHeader from './console/PageHeader';
import SectionCard from './console/SectionCard';

export default function NotFound() {
  return (
    <div>
      <PageHeader title="🔍 404 页面不存在" subtitle="你访问的页面不存在或已被移除" />
      <SectionCard title="可能的页面">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 8 }}>
          <Link to="/"><Button variant="primary">回到首页</Button></Link>
          <Link to="/projects"><Button variant="secondary">小说项目</Button></Link>
          <Link to="/books"><Button variant="secondary">拆书学习</Button></Link>
          <Link to="/factory"><Button variant="secondary">写作工厂</Button></Link>
          <Link to="/tasks"><Button variant="secondary">任务队列</Button></Link>
        </div>
        <p style={{ marginTop: 16, color: 'var(--text-muted)', fontSize: 13 }}>
          如果这是从某个页面跳转过来的，请检查链接是否正确。
        </p>
      </SectionCard>
    </div>
  );
}

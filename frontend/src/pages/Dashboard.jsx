import React, { useFetch } from 'react';
import { Link } from 'react-router-dom';
import { Icon } from '../components/ui/Icon';
import { AsyncState } from '../components/ui/AsyncState';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { useConfirm } from '../hooks/useConfirm';
import { useToast } from '../contexts/ToastContext';

import PageHeader from '../components/console/PageHeader';
import MetricCard from '../components/console/MetricCard';
import SectionCard from '../components/console/SectionCard';
import EmptyPanel from '../components/console/EmptyPanel';
import styles from './Dashboard.module.css';

const PAGE_TITLE = '仪表盘';
const PAGE_ICON = 'LayoutDashboard';
const PAGE_SUBTITLE = '欢迎来到 24小时小说 Agent 工作台';

function StatCardLocal({ icon, label, value, detail }) {
  return (
    <MetricCard label={label} value={value} hint={detail} status="info" />
  );
}

function QuickAction({ to, icon, label }) {
  return (
    <Link to={to} className={styles.actionCard}>
      <Icon name={icon} size={16} />
      <span>{label}</span>
    </Link>
  );
}

export default function Dashboard() {
  const statsState = useFetch('/dashboard/stats');
  const activityState = useFetch('/dashboard/recent-activity');
  const { confirm } = useConfirm();

  const stats = statsState.data;
  const activities = activityState.data?.activities || [];
  const loading = statsState.loading || activityState.loading;
  const error = statsState.error || activityState.error;

  const reload = () => {
    statsState.reload();
    activityState.reload();
  };

  if (!stats) return <div className={styles.page}><AsyncState loading={loading} error={error} onRetry={reload} /></div>;

  const statCards = [
    { icon: 'BookOpen', label: '项目', value: stats?.projects?.total || 0, detail: `进行中 ${stats?.projects?.active || 0} · 已完成 ${stats?.projects?.completed || 0}` },
    { icon: 'FileText', label: '章节', value: stats?.chapters?.total || 0, detail: `已完成 ${stats?.chapters?.completed || 0}` },
    { icon: 'BookOpenText', label: '总字数', value: (stats?.chapters?.total_words || 0).toLocaleString(), detail: `今日 ${(stats?.chapters?.today_words || 0).toLocaleString()}` },
    { icon: 'Bot', label: '任务', value: stats?.tasks?.total || 0, detail: `运行中 ${stats?.tasks?.running || 0} · 待处理 ${stats?.tasks?.pending || 0}` },
    { icon: 'BookOpenText', label: '已拆书籍', value: stats?.books?.total || 0, detail: `已分析 ${stats?.books?.analyzed || 0}` },
  ];

  return (
    <div className={styles.page}>
      <PageHeader title={PAGE_TITLE} subtitle={PAGE_SUBTITLE} />

      <AsyncState loading={loading} error={error} onRetry={reload} isEmpty={false}>
        <div className={styles.metricsGrid}>
          {statCards.map((s) => <StatCardLocal key={s.label} {...s} />)}
        </div>

        <div className={styles.sections}>
          <SectionCard title="快速开始">
            <div className={styles.quickActions}>
              <QuickAction to="/projects" icon="Plus" label="新建项目" />
              <QuickAction to="/books" icon="Upload" label="上传书籍" />
              <QuickAction to="/factory" icon="Play" label="启动写作" />
              <QuickAction to="/agent-orchestrator" icon="Workflow" label="自主 Agent" />
            </div>
          </SectionCard>

          <SectionCard title="最近活动">
            {activities.length === 0 ? (
              <p className={styles.empty}>暂无活动</p>
            ) : (
              <div className={styles.activityList}>
                {activities.map((activity) => (
                  <div key={activity.id} className={styles.activityItem}>
                    <span className={styles.activityType}>{activity.type}</span>
                    <span className={styles.activityStatus}>{activity.status}</span>
                    <span className={styles.activityTime}>{new Date(activity.created_at).toLocaleString()}</span>
                  </div>
                ))}
              </div>
            )}
          </SectionCard>
        </div>
      </AsyncState>
    </div>
  );
}

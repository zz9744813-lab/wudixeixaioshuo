import React from 'react';
import { Link } from 'react-router-dom';
import { Icon } from '../components/ui/Icon';
import { AsyncState } from '../components/ui/AsyncState';
import { useFetch } from '../hooks/useFetch';
import styles from './Dashboard.module.css';

export default function Dashboard() {
  const statsState = useFetch('/dashboard/stats');
  const activityState = useFetch('/dashboard/recent-activity');

  const stats = statsState.data;
  const activities = activityState.data?.activities || [];
  const loading = statsState.loading || activityState.loading;
  const error = statsState.error || activityState.error;

  const reload = () => {
    statsState.reload();
    activityState.reload();
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>
            <Icon name="LayoutDashboard" size={22} />
            <span>仪表盘</span>
          </h1>
          <p className={styles.subtitle}>欢迎来到 24小时小说 Agent 工作台</p>
        </div>
      </header>

      <AsyncState loading={loading} error={error} onRetry={reload} isEmpty={false}>
        <section className={styles.statGrid}>
          <StatCard icon="BookOpen" label="项目" value={stats?.projects?.total || 0} detail={`进行中 ${stats?.projects?.active || 0} · 已完成 ${stats?.projects?.completed || 0}`} />
          <StatCard icon="FileText" label="章节" value={stats?.chapters?.total || 0} detail={`已完成 ${stats?.chapters?.completed || 0}`} />
          <StatCard icon="FileText" label="总字数" value={(stats?.chapters?.total_words || 0).toLocaleString()} detail={`今日 ${(stats?.chapters?.today_words || 0).toLocaleString()}`} />
          <StatCard icon="Bot" label="任务" value={stats?.tasks?.total || 0} detail={`运行中 ${stats?.tasks?.running || 0} · 待处理 ${stats?.tasks?.pending || 0}`} />
          <StatCard icon="BookOpenText" label="已拆书籍" value={stats?.books?.total || 0} detail={`已分析 ${stats?.books?.analyzed || 0}`} />
        </section>

        <div className={styles.sections}>
          <section className={styles.card}>
            <h2>快速开始</h2>
            <div className={styles.quickActions}>
              <QuickAction to="/projects" icon="Plus" label="新建项目" />
              <QuickAction to="/books" icon="Upload" label="上传书籍" />
              <QuickAction to="/factory" icon="Play" label="启动写作" />
              <QuickAction to="/agent-orchestrator" icon="Workflow" label="自主 Agent" />
            </div>
          </section>

          <section className={styles.card}>
            <h2>最近活动</h2>
            <div className={styles.activityList}>
              {activities.length === 0 ? (
                <p className={styles.empty}>暂无活动</p>
              ) : (
                activities.map((activity) => (
                  <div key={activity.id} className={styles.activityItem}>
                    <span className={styles.activityType}>{activity.type}</span>
                    <span className={styles.activityStatus}>{activity.status}</span>
                    <span className={styles.activityTime}>{new Date(activity.created_at).toLocaleString()}</span>
                  </div>
                ))
              )}
            </div>
          </section>
        </div>
      </AsyncState>
    </div>
  );
}

function StatCard({ icon, label, value, detail }) {
  return (
    <div className={styles.statCard}>
      <div className={styles.statLabel}>
        <Icon name={icon} size={14} />
        <span>{label}</span>
      </div>
      <div className={styles.statValue}>{value}</div>
      <div className={styles.statDetail}>{detail}</div>
    </div>
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

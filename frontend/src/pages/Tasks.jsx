import React from 'react';
import { Link } from 'react-router-dom';
import { useFetch } from '../hooks/useFetch';
import { Icon } from '../components/ui/Icon';
import { AsyncState } from '../components/ui/AsyncState';
import { toArray } from '../utils/nullSafety';

import PageHeader from '../components/console/PageHeader';
import SectionCard from '../components/console/SectionCard';
import EmptyPanel from '../components/console/EmptyPanel';
import styles from './Tasks.module.css';

const PAGE_TITLE = '📋 任务队列';
const PAGE_SUBTITLE = '查看和管理所有任务';

export default function Tasks() {
  const { data, loading, error, reload } = useFetch('/tasks/');
  const tasks = toArray(data);

  return (
    <div className={styles.page}>
      <PageHeader title={PAGE_TITLE} subtitle={PAGE_SUBTITLE} />

      <AsyncState
        loading={loading}
        error={error}
        onRetry={reload}
        isEmpty={tasks.length === 0}
        emptyTitle="暂无任务"
        emptyHint="所有生成和写作任务将在此显示"
      >
        <SectionCard title="任务列表" subtitle={`共 ${tasks.length} 个任务`}>
          <ul className={styles.taskList}>
            {tasks.map((t) => (
              <li key={t.id} className={styles.taskItem}>
                <Link to={`/tasks/${t.id}`} className={styles.taskLink}>
                  <span className={styles.taskId}>#{t.id}</span>
                  <span className={styles.taskType}>{t.task_type}</span>
                  <span className={`${styles.taskStatus} ${styles[t.status] || ''}`}>{t.status}</span>
                  <span className={styles.taskMeta}>章节 {t.chapter_id}</span>
                </Link>
              </li>
            ))}
          </ul>
        </SectionCard>
      </AsyncState>
    </div>
  );
}

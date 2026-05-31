import React from 'react';
import { Link } from 'react-router-dom';
import { useFetch } from '../hooks/useFetch';
import { Icon } from '../components/ui/Icon';
import { AsyncState } from '../components/ui/AsyncState';
import styles from './Tasks.module.css';

const PAGE_TITLE = '📋 任务队列';

export default function Tasks() {
  const { data, loading, error, reload } = useFetch('/tasks/');
  const tasks = toArray(data);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>
          <Icon name="FileText" size={22} />
          <span>{PAGE_TITLE}</span>
        </h1>
      </header>
      <AsyncState
        loading={loading}
        error={error}
        onRetry={reload}
        isEmpty={tasks.length === 0}
        emptyTitle="暂无任务"
      >
        <div className={styles.body}>
          <ul className={styles.taskList}>
            {tasks.map((t) => (
              <li key={t.id} className={styles.taskItem}>
                <Link to={`/tasks/${t.id}`} className={styles.taskLink}>
                  <span className={styles.taskId}>#{t.id}</span>
                  <span className={styles.taskType}>{t.task_type}</span>
                  <span className={`${styles.taskStatus} ${styles[t.status] || ''}`}>
                    {t.status}
                  </span>
                  <span className={styles.taskMeta}>章节 {t.chapter_id}</span>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </AsyncState>
    </div>
  );
}

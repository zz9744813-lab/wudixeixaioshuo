import React from 'react';
import { useFetch } from '../hooks/useFetch';
import { Icon } from '../components/ui/Icon';
import { AsyncState } from '../components/ui/AsyncState';
import styles from './Techniques.module.css';

const PAGE_TITLE = '🎯 技巧库';
const PAGE_ICON = 'FileText';

export default function Techniques() {
  const { data, loading, error, reload } = useFetch('/techniques/');
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>
          <Icon name={PAGE_ICON} size={22} />
          <span>{PAGE_TITLE}</span>
        </h1>
      </header>
      <AsyncState loading={loading} error={error} onRetry={reload} isEmpty={!data} emptyTitle="暂无数据">
        <div className={styles.body}>
          <p className={styles.placeholder}>页面开发中 · {PAGE_TITLE}</p>
        </div>
      </AsyncState>
    </div>
  );
}

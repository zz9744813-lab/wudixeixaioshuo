import React from 'react';
import { Icon } from '../components/ui/Icon';
import { AsyncState } from '../components/ui/AsyncState';
import styles from './WritingFactory.module.css';

const PAGE_TITLE = '🏭 24小时写作工厂';
const PAGE_ICON = 'FileText';

export default function WritingFactory() {
    return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>
          <Icon name={PAGE_ICON} size={22} />
          <span>{PAGE_TITLE}</span>
        </h1>
      </header>
      <AsyncState loading={false} error={null} onRetry={() => {}} isEmpty={true} emptyTitle="暂无数据">
        <div className={styles.body}>
          <p className={styles.placeholder}>页面开发中 · {PAGE_TITLE}</p>
        </div>
      </AsyncState>
    </div>
  );
}

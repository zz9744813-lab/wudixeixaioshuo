import React, { useState } from 'react';
import { useFetch } from '../hooks/useFetch';
import { AsyncState } from '../components/ui/AsyncState';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Link } from 'react-router-dom';
import api from '../services/api';
import { useToast } from '../contexts/ToastContext';
import { toObject, toArray } from '../utils/nullSafety';

import PageHeader from '../components/console/PageHeader';
import MetricCard from '../components/console/MetricCard';
import SectionCard from '../components/console/SectionCard';
import EmptyPanel from '../components/console/EmptyPanel';
import styles from './Techniques.module.css';

const PAGE_TITLE = '🎯 技巧库';
const PAGE_ICON = 'FileText';
const PAGE_SUBTITLE = '管理各角色的 Prompt 模板';

const ROLE_LABELS = {
  planner: 'Planner',
  draft: 'Draft',
  critic: 'Critic',
  rewrite: 'Rewrite',
  continuity: 'Continuity',
  memory_update: 'Memory Update',
};

const CATEGORY_COLORS = {
  '人物塑造': 'success',
  '情节推进': 'warning',
  '对话技巧': 'accent',
  '氛围营造': 'info',
  '伏笔埋设': 'danger',
};

export default function Techniques() {
  const [selectedCategory, setSelectedCategory] = useState('');
  const [detailId, setDetailId] = useState(null);
  const [detailData, setDetailData] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const toast = useToast();

  const { data: techniques = [], loading, error, reload } = useFetch(
    selectedCategory ? `/techniques/?category=${encodeURIComponent(selectedCategory)}` : '/techniques/'
  );
  const { data: categories = [], loading: loadingCats } = useFetch('/techniques/categories');

  const openDetail = async (id) => {
    setDetailId(id);
    setLoadingDetail(true);
    setDetailData(null);
    try {
      const res = await api.get(`/techniques/${id}`);
      setDetailData(res.data);
    } catch (err) {
      toast.error('加载技巧详情失败');
    } finally {
      setLoadingDetail(false);
    }
  };

  const columns = [
    { key: 'title', label: '技巧名称' },
    { key: 'category', label: '分类', render: (v) => <Badge variant={CATEGORY_COLORS[v] || 'accent'}>{v}</Badge> },
    { key: 'confidence_score', label: '置信度', align: 'right', render: (v) => `${(v * 100).toFixed(0)}%` },
    { key: 'usage_count', label: '使用次数', align: 'right' },
    { key: 'status', label: '状态', render: (v) => <Badge variant={v ? 'success' : 'muted'}>{v ? '启用' : '停用'}</Badge> },
    { key: 'created_at', label: '创建时间', render: (v) => v ? new Date(v).toLocaleDateString('zh-CN') : '-' },
  ];

  const stats = React.useMemo(() => {
    const total = techniques.length;
    const avgConfidence = total ? (techniques.reduce((s, t) => s + (t.confidence_score || 0), 0) / total * 100).toFixed(0) : 0;
    const totalUsage = techniques.reduce((s, t) => s + (t.usage_count || 0), 0);
    return [
      { label: '技巧总数', value: total },
      { label: '平均置信度', value: avgConfidence, unit: '%' },
      { label: '总使用次数', value: totalUsage },
    ];
  }, [techniques]);

  return (
    <div className={styles.page}>
      <PageHeader
        title={PAGE_TITLE}
        subtitle={PAGE_SUBTITLE}
        actions={
          <Link to="/books"><Button variant="secondary" size="sm">从书籍导入</Button></Link>
        }
      />

      <div className={styles.metricsRow}>
        {stats.map((s) => <MetricCard key={s.label} label={s.label} value={s.value} unit={s.unit || ''} status="info" />)}
      </div>

      <SectionCard title="技巧列表" subtitle={selectedCategory ? `${selectedCategory} 分类` : '全部角色'}>
        <div className={styles.filterBar}>
          <span className={styles.filterLabel}>分类：</span>
          <div className={styles.categoryList}>
            <button
              className={`${styles.catChip} ${!selectedCategory ? styles.catChipActive : ''}`}
              onClick={() => setSelectedCategory('')}
            >全部</button>
            {(categories || []).map((cat) => (
              <button
                key={cat}
                className={`${styles.catChip} ${selectedCategory === cat ? styles.catChipActive : ''}`}
                onClick={() => setSelectedCategory(cat)}
              >{cat}</button>
            ))}
          </div>
        </div>
        <AsyncState loading={loading} error={error} onRetry={reload} isEmpty={!techniques.length} emptyTitle="暂无技巧卡"
          emptyHint="请先上传书籍或添加技巧">
          <Table columns={columns} rows={techniques} rowKey="id" onRowClick={(row) => openDetail(row.id)} />
        </AsyncState>
      </SectionCard>

      <Modal open={!!detailId} onClose={() => setDetailId(null)} title={detailData?.title || '技巧详情'}>
        {loadingDetail ? (
          <div className={styles.detailSkeleton} />
        ) : detailData ? (
          <div className={styles.detailBody}>
            {detailData.description && <p className={styles.detailDesc}>{detailData.description}</p>}
            {detailData.observation && <section className={styles.detailSection}><h4>观察</h4><p>{detailData.observation}</p></section>}
            {detailData.principle && <section className={styles.detailSection}><h4>原理</h4><p>{detailData.principle}</p></section>}
            {detailData.usage_instruction && <section className={styles.detailSection}><h4>使用说明</h4><p>{detailData.usage_instruction}</p></section>}
            {detailData.transfer_rule && <section className={styles.detailSection}><h4>迁移规则</h4><p>{detailData.transfer_rule}</p></section>}
            {detailData.anti_pattern && <section className={styles.detailSection}><h4>反模式</h4><p>{detailData.anti_pattern}</p></section>}
            {detailData.applicable_genres && <section className={styles.detailSection}><h4>适用题材</h4><Badge variant="accent">{detailData.applicable_genres}</Badge></section>}
            <div className={styles.detailMeta}>
              <span>置信度：{(detailData.confidence_score * 100).toFixed(0)}%</span>
              <span>使用：{detailData.usage_count} 次</span>
              <span>成功率：{(detailData.success_rate * 100 || 0).toFixed(0)}%</span>
            </div>
          </div>
        ) : null}
      </Modal>
    </div>
  );
}

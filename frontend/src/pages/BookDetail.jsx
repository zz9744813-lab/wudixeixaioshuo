import React, { useState, useCallback, useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import api from '../services/api';
import { useToast } from '../contexts/ToastContext';
import { useConfirm } from '../hooks/useConfirm';
import ConfirmModal from '../components/ConfirmModal';
import Modal from '../components/ui/Modal';
import { toArray } from '../utils/nullSafety';

import PageHeader from '../components/console/PageHeader';
import MetricCard from '../components/console/MetricCard';
import SectionCard from '../components/console/SectionCard';
import EmptyPanel from '../components/console/EmptyPanel';
import styles from './BookDetail.module.css';

const PAGE_TITLE = '书籍详情';
const PAGE_ICON = 'BookOpen';
const PAGE_SUBTITLE = '拆书学习详情';

const BOOK_STATUS = {
  imported: { label: '已导入', variant: 'accent' },
  splitting: { label: '分章中...', variant: 'warning' },
  split_completed: { label: '分章完成', variant: 'success' },
  analyzing: { label: '分析中...', variant: 'warning' },
  completed: { label: '分析完成', variant: 'success' },
  failed: { label: '失败', variant: 'danger' },
};

export default function BookDetail() {
  const { id } = useParams();
  const bookId = Number(id);
  const toast = useToast();
  const { confirm, state: confirmState, handleOk, handleCancel } = useConfirm();

  const [book, setBook] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showChapter, setShowChapter] = useState(null);
  const [activeTab, setActiveTab] = useState('chapters');

  const fetchBook = useCallback(async () => {
    if (!bookId) return;
    setLoading(true);
    setError('');
    try {
      const res = await api.get(`/books/${bookId}`);
      setBook(res.data);
    } catch (err) {
      const msg = err?.response?.data?.detail || err.message || '加载失败';
      setError(msg);
    } finally { setLoading(false); }
  }, [bookId]);

  useEffect(() => { fetchBook(); }, [fetchBook]);

  const handleSplit = async () => {
    toast.info('开始智能分章...', 4000);
    try {
      const res = await api.post(`/books/${bookId}/split`);
      toast.success(res.data?.message || '分章完成', 5000);
      fetchBook();
    } catch (err) { toast.error(err?.response?.data?.detail || '分章失败', 6000); }
  };

  const handleAnalyze = async () => {
    toast.info('开始拆书分析，这可能需要几分钟...', 5000);
    try {
      const res = await api.post(`/books/${bookId}/analyze`);
      toast.success(res.data?.message || '分析完成', 5000);
      fetchBook();
    } catch (err) { toast.error(err?.response?.data?.detail || '分析失败', 6000); }
  };

  const handleExtract = async () => {
    toast.info('正在提取写作技巧卡...', 4000);
    try {
      const res = await api.post(`/books/${bookId}/extract-techniques`);
      toast.success(res.data?.message || '技巧提取完成', 5000);
      window.location.href = `/techniques?book_id=${bookId}`;
    } catch (err) { toast.error(err?.response?.data?.detail || '提取失败', 6000); }
  };

  const handleDelete = async () => {
    const ok = await confirm({ title: '删除书籍', message: `确定要删除书籍「${book?.title || ''}」吗？相关文件和数据将被清除。` });
    if (!ok) return;
    try {
      await api.del(`/books/${bookId}`);
      toast.success('书籍已删除');
      window.location.href = '/books';
    } catch (err) { toast.error(err?.response?.data?.detail || '删除失败', 6000); }
  };

  const handleFetchChapter = async (ch) => {
    setShowChapter(null);
    try {
      const res = await api.get(`/books/${bookId}/chapters/${ch.id}`);
      setShowChapter(res.data);
    } catch (err) {
      toast.error(err?.response?.data?.detail || '获取章节详情失败', 5000);
    }
  };

  if (!bookId) return <div className={styles.page}><p className={styles.err}>无效的书籍 ID</p></div>;

  const st = BOOK_STATUS[book?.status] || BOOK_STATUS.imported;
  const chapters = toArray(book?.chapters);
  const analysisReport = book?.analysis_report || null;

  const metricsCards = [
    { label: '总章节', value: book?.total_chapters || 0 },
    { label: '总字数', value: (book?.total_words || 0).toLocaleString(), unit: '字' },
    { label: '分析进度', value: `${book?.analysis_progress || 0}%` },
  ];

  const tabBar = (
    <div className={styles.tabBar}>
      <button className={`${styles.tab} ${activeTab === 'chapters' ? styles.tabActive : ''}`} onClick={() => setActiveTab('chapters')}>章节列表</button>
      <button className={`${styles.tab} ${activeTab === 'analysis' ? styles.tabActive : ''}`} onClick={() => setActiveTab('analysis')}>拆书数据</button>
      {analysisReport && <button className={`${styles.tab} ${activeTab === 'report' ? styles.tabActive : ''}`} onClick={() => setActiveTab('report')}>分析报告</button>}
    </div>
  );

  return (
    <div className={styles.page}>
      <PageHeader
        title={book?.title || PAGE_TITLE}
        subtitle={PAGE_SUBTITLE}
        actions={
          <Link to="/books"><Button variant="secondary" size="sm">← 返回书籍列表</Button></Link>
        }
      />

      <AsyncState loading={loading} error={error} onRetry={fetchBook} isEmpty={false}>
        <div className={styles.headerMeta}>
          <Badge variant={st.variant}>{st.label}</Badge>
          <span>作者：{book?.author_alias || '未知'}</span>
          <span>题材：{book?.genre || '-'}</span>
          <span>来源：{book?.source_type || '-'}</span>
        </div>

        <div className={styles.metricsGrid}>
          {metricsCards.map((m) => <MetricCard key={m.label} label={m.label} value={m.value} unit={m.unit || ''} />)}
        </div>

        <SectionCard title="操作区" actions={tabBar}>
          <div className={styles.actionGrid}>
            {!chapters.length && book?.status !== 'splitting' && <Button variant="primary" onClick={handleSplit}>智能分章</Button>}
            {chapters.length > 0 && !['analyzing', 'completed'].includes(book?.status) && <Button variant="primary" onClick={handleAnalyze}>拆书分析</Button>}
            {book?.status === 'completed' && <Button variant="primary" onClick={handleExtract}>提取技巧卡</Button>}
            {['splitting', 'analyzing'].includes(book?.status) && <Badge variant="warning">处理中...</Badge>}
            <Button variant="danger" onClick={handleDelete}>删除书籍</Button>
          </div>
        </SectionCard>

        {activeTab === 'chapters' && (
          <SectionCard title="章节列表" subtitle={`共 ${chapters.length} 章`}>
            <AsyncState loading={false} error={null} isEmpty={chapters.length === 0} emptyTitle="暂无章节，请先进行分章" hideLoading hideError>
              <div className={styles.chapterList}>
                {chapters.map((ch) => (
                  <div key={ch.id} className={styles.chapterItem} onClick={() => handleFetchChapter(ch)}>
                    <span className={styles.chapterIndex}>#{ch.index || ch.chapter_index}</span>
                    <span className={styles.chapterTitle}>{ch.title || '未命名章节'}</span>
                    <span className={styles.chapterWord}>{ch.word_count || 0} 字</span>
                    <Button variant="ghost" size="sm">详情</Button>
                  </div>
                ))}
              </div>
            </AsyncState>
          </SectionCard>
        )}

        {activeTab === 'analysis' && (
          <SectionCard title="拆书数据" subtitle="章节概览、人物、钩子">
            {chapters.length === 0 ? (
              <p className={styles.empty}>暂无数据，请先执行拆书分析</p>
            ) : (
              <div className={styles.analysisGrid}>
                <div className={styles.analysisSection}>
                  <h4 className={styles.analysisTitle}>章节概览</h4>
                  <div className={styles.chapterList}>
                    {chapters.slice(0, 20).map((ch) => (
                      <div key={ch.id} className={styles.chapterItem} onClick={() => handleFetchChapter(ch)}>
                        <span className={styles.chapterIndex}>#{ch.index || ch.chapter_index}</span>
                        <span className={styles.chapterTitle}>{ch.title}</span>
                        {ch.summary && <span className={styles.chapterWord} title={ch.summary}>{ch.summary.slice(0, 40)}...</span>}
                      </div>
                    ))}
                  </div>
                </div>
                <div className={styles.analysisSection}>
                  <h4 className={styles.analysisTitle}>人物 / 剧情点 / 钩子</h4>
                  {chapters.length === 0 || !chapters[0]?.character_mentions ? (
                    <p className={styles.empty}>暂无数据</p>
                  ) : (
                    <div>
                      <p><strong>人物提及：</strong>{(() => { const names = chapters.slice(0, 5).flatMap((ch) => ch.character_mentions || []); return [...new Set(names)].join('、') || '无'; })()}</p>
                      <p style={{ marginTop: 8 }}><strong>钩子类型：</strong>{(() => { const types = chapters.slice(0, 5).flatMap((ch) => (ch.hooks || []).map((h) => h?.type || h?.description || '未知')); return [...new Set(types)].join('、') || '无'; })()}</p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </SectionCard>
        )}

        {activeTab === 'report' && analysisReport && (
          <SectionCard title="分析报告">
            <pre className={styles.analysisBody}>{analysisReport}</pre>
          </SectionCard>
        )}
      </AsyncState>

      <Modal open={!!showChapter} onClose={() => setShowChapter(null)} title={`第 ${showChapter?.chapter_index} 章：${showChapter?.title || ''}`} size="lg" footer={<Button variant="secondary" onClick={() => setShowChapter(null)}>关闭</Button>}>
        <div className={styles.chapterDetail}>
          {showChapter?.summary && <p><strong>摘要：</strong>{showChapter.summary}</p>}
          {showChapter?.structure_analysis && <pre className={styles.analysisBody}>{JSON.stringify(showChapter.structure_analysis, null, 2)}</pre>}
          {showChapter?.character_mentions?.length > 0 && <p><strong>人物：</strong>{showChapter.character_mentions.join('、')}</p>}
          {showChapter?.plot_points?.length > 0 && <p><strong>剧情点：</strong>{showChapter.plot_points.join('、')}</p>}
          {showChapter?.emotional_beats?.length > 0 && <p><strong>情绪节拍：</strong>{showChapter.emotional_beats.map((e) => `${e.position}: ${e.emotion}(${e.intensity})`).join(' | ')}</p>}
          {showChapter?.hooks?.length > 0 && <div><strong>钩子：</strong>{showChapter.hooks.map((h, i) => <span key={i} className={styles.hookTag}>{h?.type || h?.description || '未知'}</span>)}</div>}
          <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '12px 0' }} />
          <pre className={styles.analysisBody}>{(showChapter?.content || '').slice(0, 4000)}{(showChapter?.content || '').length > 4000 ? '\n\n...(内容已截断)' : ''}</pre>
        </div>
      </Modal>

      <ConfirmModal state={confirmState} onOk={handleOk} onCancel={handleCancel} />
    </div>
  );
}

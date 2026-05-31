import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useToast } from '../contexts/ToastContext';
import { useConfirm } from '../hooks/useConfirm';
import { AsyncState } from '../components/ui/AsyncState';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import ConfirmModal from '../components/ConfirmModal';
import Modal from '../components/ui/Modal';
import { toArray } from '../utils/nullSafety';

import PageHeader from '../components/console/PageHeader';
import SectionCard from '../components/console/SectionCard';
import EmptyPanel from '../components/console/EmptyPanel';
import styles from './Books.module.css';

const PAGE_TITLE = '📚 拆书学习';
const PAGE_ICON = 'BookOpen';
const PAGE_SUBTITLE = '上传书籍 → 智能分章 → 拆书分析 → 提取技巧';

const SOURCE_TYPES = [
  { value: 'txt', label: 'TXT 文本' },
  { value: 'md', label: 'Markdown' },
  { value: 'epub', label: 'EPUB 电子书' },
  { value: 'docx', label: 'DOCX Word' },
  { value: 'pdf', label: 'PDF' },
];

const BOOK_STATUS = {
  imported: { label: '已导入', variant: 'accent' },
  splitting: { label: '分章中...', variant: 'warning' },
  split_completed: { label: '分章完成', variant: 'success' },
  analyzing: { label: '分析中...', variant: 'warning' },
  completed: { label: '分析完成', variant: 'success' },
  failed: { label: '失败', variant: 'danger' },
};

export default function Books() {
  const navigate = useNavigate();
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const fileInputRef = useRef(null);

  const [createTitle, setCreateTitle] = useState('');
  const [createAuthor, setCreateAuthor] = useState('');
  const [createGenre, setCreateGenre] = useState('');
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploadGenre, setUploadGenre] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const toast = useToast();
  const { confirm, state: confirmState, handleOk, handleCancel } = useConfirm();

  const fetchBooks = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.get('/books/');
      setBooks(toArray(res.data));
    } catch (err) {
      const msg = err?.response?.data?.detail || err.message || '加载书籍列表失败';
      setError(msg);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchBooks(); }, [fetchBooks]);

  const handleUpload = async () => {
    if (!uploadFile) { toast.error('请选择文件', 4000); return; }
    setSubmitting(true);
    try {
      const form = new FormData();
      form.append('file', uploadFile);
      if (uploadTitle.trim()) form.append('title', uploadTitle.trim());
      if (uploadGenre.trim()) form.append('genre', uploadGenre.trim());
      const res = await api.post('/books/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      toast.success(res.data?.message || '上传成功', 4000);
      setShowCreate(false);
      setUploadFile(null); setUploadTitle(''); setUploadGenre('');
      fetchBooks();
    } catch (err) {
      const msg = err?.response?.data?.detail || err.message || '上传失败';
      toast.error(msg, 6000);
    } finally { setSubmitting(false); }
  };

  const handleCreate = async () => {
    if (!createTitle.trim()) { toast.error('请填写书名', 4000); return; }
    setSubmitting(true);
    try {
      await api.post('/books/', {
        title: createTitle.trim(),
        author_alias: createAuthor.trim() || undefined,
        genre: createGenre.trim() || undefined,
        source_type: 'txt',
      });
      toast.success('书籍已创建');
      setShowCreate(false);
      setCreateTitle(''); setCreateAuthor(''); setCreateGenre('');
      fetchBooks();
    } catch (err) {
      toast.error(err?.response?.data?.detail || err.message || '创建失败', 6000);
    } finally { setSubmitting(false); }
  };

  const handleSplit = async (bookId) => {
    toast.info('开始智能分章，请稍候...', 4000);
    try {
      const res = await api.post(`/books/${bookId}/split`);
      toast.success(res.data?.message || '分章完成', 5000);
      fetchBooks();
    } catch (err) {
      toast.error(err?.response?.data?.detail || err.message || '分章失败', 6000);
    }
  };

  const handleAnalyze = async (bookId) => {
    toast.info('开始拆书分析，这可能需要几分钟...', 5000);
    try {
      const res = await api.post(`/books/${bookId}/analyze`);
      toast.success(res.data?.message || '分析完成', 5000);
      fetchBooks();
    } catch (err) {
      toast.error(err?.response?.data?.detail || err.message || '分析失败', 6000);
    }
  };

  const handleExtract = async (bookId) => {
    toast.info('正在提取写作技巧卡...', 4000);
    try {
      const res = await api.post(`/books/${bookId}/extract-techniques`);
      toast.success(res.data?.message || '技巧提取完成', 5000);
      navigate(`/techniques?book_id=${bookId}`);
    } catch (err) {
      toast.error(err?.response?.data?.detail || err.message || '提取失败', 6000);
    }
  };

  const handleDelete = async (id, title) => {
    const ok = await confirm({ title: '删除书籍', message: `确定要删除书籍「${title || id}」吗？相关文件和数据将被清除。` });
    if (!ok) return;
    try {
      await api.del(`/books/${id}`);
      toast.success('书籍已删除');
      fetchBooks();
    } catch (err) { toast.error(err?.response?.data?.detail || '删除失败', 6000); }
  };

  const statusOf = (s) => BOOK_STATUS[s] || { label: s || '未知', variant: 'muted' };

  return (
    <div className={styles.page}>
      <PageHeader
        title={PAGE_TITLE}
        subtitle={PAGE_SUBTITLE}
        actions={
          <Button variant="primary" size="sm" onClick={() => { setCreateTitle(''); setCreateAuthor(''); setCreateGenre(''); setUploadFile(null); setShowCreate(true); }}>
            + 添加书籍
          </Button>
        }
      />

      <AsyncState loading={loading} error={error} onRetry={fetchBooks} isEmpty={books.length === 0} emptyTitle="暂无书籍"
        emptyHint="上传第一本书开始拆书学习">
        <SectionCard title="书籍列表" subtitle={`共 ${books.length} 本书`}>
          <div className={styles.grid}>
            {books.map((b) => {
              const st = statusOf(b.status);
              return (
                <div key={b.id} className={styles.card}>
                  <div className={styles.cardTop}>
                    <Link to={`/books/${b.id}`} className={styles.cardTitle}>{b.title}</Link>
                    <Badge variant={st.variant}>{st.label}</Badge>
                  </div>
                  <div className={styles.cardBody}>
                    <div className={styles.metaRow}><span className={styles.metaLabel}>作者</span><span>{b.author_alias || '未知'}</span></div>
                    <div className={styles.metaRow}><span className={styles.metaLabel}>题材</span><span>{b.genre || '-'}</span></div>
                    <div className={styles.metaRow}><span className={styles.metaLabel}>来源</span><span>{SOURCE_TYPES.find((t) => t.value === b.source_type)?.label || b.source_type}</span></div>
                    <div className={styles.metaRow}><span className={styles.metaLabel}>章节/字数</span><span>{b.total_chapters || 0} 章 / {(b.total_words || 0).toLocaleString()} 字</span></div>
                    <div className={styles.metaRow}><span className={styles.metaLabel}>创建时间</span><span>{b.created_at ? new Date(b.created_at).toLocaleDateString() : '-'}</span></div>
                  </div>
                  <div className={styles.cardActions}>
                    <Link to={`/books/${b.id}`}><Button variant="secondary" size="sm">详情</Button></Link>
                    {b.status === 'imported' && (
                      <Button variant="primary" size="sm" onClick={() => handleSplit(b.id)}>智能分章</Button>
                    )}
                    {b.status === 'split_completed' && (
                      <Button variant="primary" size="sm" onClick={() => handleAnalyze(b.id)}>拆书分析</Button>
                    )}
                    {b.status === 'completed' && (
                      <Button variant="primary" size="sm" onClick={() => handleExtract(b.id)}>提取技巧</Button>
                    )}
                    {['splitting', 'analyzing'].includes(b.status) && (
                      <Badge variant="warning">处理中...</Badge>
                    )}
                    <Button variant="danger" size="sm" onClick={() => handleDelete(b.id, b.title)}>删除</Button>
                  </div>
                </div>
              );
            })}
          </div>
        </SectionCard>
      </AsyncState>

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="添加书籍" size="md" footer={
        <div className={styles.modalActions}>
          <Button variant="primary" onClick={handleUpload} disabled={submitting}>{submitting ? '上传中…' : '上传文件'}</Button>
          <Button variant="secondary" onClick={() => { setShowCreate(false); }}>关闭</Button>
        </div>
      }>
        <div className={styles.formGrid}>
          <label className={styles.fullWidth}>
            <span>选择文件（TXT/EPUB/DOCX/PDF）</span>
            <input type="file" accept=".txt,.md,.epub,.docx,.pdf" onChange={(e) => { const f = e.target.files?.[0]; if (f) { setUploadFile(f); setUploadTitle(f.name.replace(/\.[^.]+$/, '')); } }} />
          </label>
          <label>
            <span>书名（上传时自动填充，可修改）</span>
            <input value={uploadTitle} onChange={(e) => setUploadTitle(e.target.value)} placeholder="书名" />
          </label>
          <label>
            <span>题材</span>
            <input value={uploadGenre} onChange={(e) => setUploadGenre(e.target.value)} placeholder="玄幻 / 都市 / 科幻..." />
          </label>
          <div className={styles.divider}>- 或 手动创建（粘贴文本前先用上传导入） -</div>
          <label>
            <span>书名</span>
            <input value={createTitle} onChange={(e) => setCreateTitle(e.target.value)} placeholder="书名" />
          </label>
          <label>
            <span>作者</span>
            <input value={createAuthor} onChange={(e) => setCreateAuthor(e.target.value)} placeholder="作者或别名" />
          </label>
          <label>
            <span>题材</span>
            <input value={createGenre} onChange={(e) => setCreateGenre(e.target.value)} placeholder="题材" />
          </label>
          <div className={styles.modalActions} style={{ gridColumn: '1 / -1', justifyContent: 'flex-start' }}>
            <Button variant="accent" size="sm" onClick={handleCreate} disabled={submitting || !createTitle.trim()}>创建记录</Button>
          </div>
        </div>
      </Modal>

      <ConfirmModal state={confirmState} onOk={handleOk} onCancel={handleCancel} />
    </div>
  );
}

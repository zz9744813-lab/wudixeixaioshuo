import { useState } from 'react';
import { useFetch } from '../hooks/useFetch';
import { Icon } from '../components/ui/Icon';
import { AsyncState } from '../components/ui/AsyncState';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import Modal from '../components/ui/Modal';
import { Table } from '../components/ui/Table';
import api from '../services/api';
import { useToast } from '../contexts/ToastContext';
import styles from './ExportPage.module.css';

const PAGE_TITLE = '小说导出中心';
const PAGE_ICON = 'Download';
const FORMAT_LABELS = { md: 'Markdown', txt: '纯文本', docx: 'Word', epub: 'EPUB', pdf: 'PDF', json: 'JSON' };

export default function ExportPage() {
  const toast = useToast();
  const [projectId, setProjectId] = useState('');
  const [selectedFormat, setSelectedFormat] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [history, setHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const { data: projects = [], loading: loadingProjects } = useFetch('/projects/');
  const { data: formats } = useFetch('/export/formats');

const selectedProject = projects.find(p => String(p.id) === projectId);
      const fetchHistory = async (pid) => {
    setLoadingHistory(true);
    try {
      const res = await api.get('/export/history');
      setHistory(res.data.exports || []);
    } catch {
      setHistory([]);
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleExport = async (formatId) => {
    if (!projectId) { toast.error('请先选择项目'); return; }
    if (!formatId) { toast.error('请选择导出格式'); return; }
    setSubmitting(true);
    try {
      const res = await api.post('/export/', {
        project_id: Number(projectId),
        format: formatId,
        include_outline: true,
        include_metadata: true,
      });
      const filename = res.data.filename;
      if (filename) {
        const baseUrl = (process.env.REACT_APP_API_URL || 'http://localhost:8000/api').replace(/\/$/, '');
        window.open(`${baseUrl}/export/download/${encodeURIComponent(filename)}`, '_blank');
      }
      toast.success(res.data?.message || '导出成功');
      fetchHistory(projectId);
    } catch (err) {
      toast.error(err?.response?.data?.detail || '导出失败', 6000);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (filename) => {
    try {
      await api.delete(`/export/${encodeURIComponent(filename)}`);
      toast.success('文件已删除');
      fetchHistory(projectId);
    } catch {
      toast.error('删除失败');
    }
  };

  const historyColumns = [
    { key: 'id', label: 'ID', align: 'right' },
    { key: 'format', label: '格式', render: (v) => <Badge variant="accent">{FORMAT_LABELS[v] || v}</Badge> },
    { key: 'created_at', label: '导出时间', render: (v) => v ? new Date(v).toLocaleString('zh-CN') : '-' },
    { key: 'filename', label: '文件', render: (v) => v ? (
      <a href={`/export/download/${encodeURIComponent(v)}`} target="_blank" rel="noreferrer">下载</a>
    ) : '-' },
    { key: 'word_count', label: '字数', align: 'right', render: (v) => (v ? Number(v).toLocaleString() : '-') + ' 字' },
    { key: 'status', label: '状态', render: (v) => <Badge variant={v === 'success' ? 'success' : 'danger'}>{v || '-'}</Badge> },
  ];

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}><Icon name={PAGE_ICON} size={22} /><span>{PAGE_TITLE}</span></h1>
      </header>

      <div className={styles.body}>
        <div className={styles.filterBar}>
          <span>项目：</span>
          <select className={styles.select} value={projectId} onChange={(e) => setProjectId(e.target.value)}>
            <option value="">-- 选择项目 --</option>
            {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
        {selectedProject && (
          <p className={styles.currentHint}>当前项目：<strong>{selectedProject.name}</strong></p>
        )}

        <AsyncState loading={loadingProjects} isEmpty={!projects.length} emptyTitle="暂无项目" hideLoading hideError>
          <section className={styles.section}>
            <h3 className={styles.cardTitle}>导出格式</h3>
            <div className={styles.formatGrid}>
              {(formats?.formats || []).map((f) => (
                <div key={f.id} className={styles.formatCard}>
                  <strong>{f.name}</strong>
                  <span className={styles.formatHint}>{f.description}</span>
                  <Button
                    variant="primary"
                    size="sm"
                    loading={submitting}
                    onClick={() => handleExport(f.id)}
                    disabled={!projectId}
                  >
                    导出 {f.extension}
                  </Button>
                </div>
              ))}
            </div>
          </section>
        </AsyncState>

        <section className={styles.section}>
          <h3 className={styles.cardTitle}>导出记录</h3>
          <AsyncState loading={loadingHistory} isEmpty={!history.length} emptyTitle="暂无导出记录">
            <Table columns={historyColumns} rows={history} rowKey="id" />
          </AsyncState>
        </section>
      </div>
    </div>
  );
}

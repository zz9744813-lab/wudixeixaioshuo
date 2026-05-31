import React, { useEffect, useState } from 'react';
import { useFetch } from '../hooks/useFetch';
import { AsyncState } from '../components/ui/AsyncState';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Table } from '../components/ui/Table';
import { useToast } from '../contexts/ToastContext';
import { toArray, toObject } from '../utils/nullSafety';
import api, { API_BASE_URL, getApiErrorMessage } from '../services/api';

import PageHeader from '../components/console/PageHeader';
import SectionCard from '../components/console/SectionCard';
import EmptyPanel from '../components/console/EmptyPanel';
import styles from './ExportPage.module.css';

const PAGE_TITLE = '小说导出中心';
const PAGE_SUBTITLE = '多格式导出 → 一键下载';

const apiBase = API_BASE_URL.replace(/\/$/, '');

function getDownloadUrl(filename) {
  return `${apiBase}/export/download/${encodeURIComponent(filename)}`;
}

const FORMAT_LABELS = {
  md: 'Markdown',
  txt: '纯文本',
  docx: 'Word',
  epub: 'EPUB',
  pdf: 'PDF',
  json: 'JSON',
};

export default function ExportPage() {
  const toast = useToast();
  const [projectId, setProjectId] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [history, setHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const { data: rawProjects, loading: loadingProjects } = useFetch('/projects/', { initialData: [] });
  const { data: rawFormats } = useFetch('/export/formats', { initialData: { formats: [] } });

  const projects = toArray(rawProjects);
  const formats = toArray(toObject(rawFormats).formats);
  const selectedProject = projects.find((p) => String(p.id) === projectId);

  useEffect(() => {
    if (projectId) fetchHistory(projectId);
  }, [projectId]);

  const fetchHistory = async (pid) => {
    setLoadingHistory(true);
    try {
      const res = await api.get(`/export/history?project_id=${pid}`);
      const data = res.data || {};
      setHistory(toArray(data?.exports));
    } catch (err) {
      toast.error(getApiErrorMessage(err) || '加载导出记录失败', 5000);
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
      const filename = res.data?.filename;
      if (filename) {
        window.open(getDownloadUrl(filename), '_blank');
      }
      toast.success(res.data?.message || '导出成功');
      fetchHistory(projectId);
    } catch (err) {
      toast.error(getApiErrorMessage(err) || '导出失败', 6000);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (filename) => {
    try {
      await api.delete(`/export/${encodeURIComponent(filename)}`);
      toast.success('文件已删除');
      fetchHistory(projectId);
    } catch (err) {
      toast.error(getApiErrorMessage(err) || '删除失败', 6000);
    }
  };

  const historyColumns = [
    { key: 'id', label: 'ID', align: 'right' },
    { key: 'format', label: '格式', render: (v) => <Badge variant="accent">{FORMAT_LABELS[v] || v}</Badge> },
    { key: 'created_at', label: '导出时间', render: (v) => v ? new Date(v).toLocaleString('zh-CN') : '-' },
    { key: 'filename', label: '文件', render: (v) => v ? (
      <a href={getDownloadUrl(v)} target="_blank" rel="noreferrer">下载</a>
    ) : '-' },
    { key: 'word_count', label: '字数', align: 'right', render: (v) => (v ? Number(v).toLocaleString() : '-') + ' 字' },
    { key: 'status', label: '状态', render: (v) => <Badge variant={v === 'success' ? 'success' : 'danger'}>{v || '-'}</Badge> },
  ];

  return (
    <div className={styles.page}>
      <PageHeader
        title={PAGE_TITLE}
        subtitle={PAGE_SUBTITLE}
        actions={
          <select className={styles.select} value={projectId} onChange={(e) => setProjectId(e.target.value)}>
            <option value="">-- 选择项目 --</option>
            {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        }
      />

      {selectedProject && (
        <div className={styles.hint}>当前项目：<strong>{selectedProject.name}</strong></div>
      )}

      <AsyncState loading={loadingProjects} isEmpty={!projects.length} emptyTitle="暂无项目" hideLoading hideError>
        <SectionCard title="导出格式" subtitle={`支持 ${formats.length} 种格式`}>
          <div className={styles.formatGrid}>
            {formats.map((f) => (
              <div key={f.id} className={styles.formatCard}>
                <div className={styles.formatInfo}>
                  <strong>{f.name || FORMAT_LABELS[f.id]}</strong>
                  <span className={styles.formatHint}>{f.description}</span>
                </div>
                <Button variant="primary" size="sm" loading={submitting} onClick={() => handleExport(f.id)} disabled={!projectId}>
                  导出 {f.extension || f.id}
                </Button>
              </div>
            ))}
          </div>
        </SectionCard>
      </AsyncState>

      <SectionCard title="导出记录" subtitle={history.length > 0 ? `共 ${history.length} 条记录` : ''}>
        <AsyncState loading={loadingHistory} isEmpty={!history.length} emptyTitle="暂无导出记录">
          <Table columns={historyColumns} rows={history} rowKey="id" />
        </AsyncState>
      </SectionCard>
    </div>
  );
}

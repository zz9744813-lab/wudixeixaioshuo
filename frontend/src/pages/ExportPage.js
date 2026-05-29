import React, { useState, useEffect } from 'react';
import api from '../services/api';
import './ExportPage.css';

function ExportPage() {
  const [projects, setProjects] = useState([]);
  const [formats, setFormats] = useState([]);
  const [history, setHistory] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [exportConfig, setExportConfig] = useState({
    project_id: '',
    format: 'md',
    include_outline: true,
    include_metadata: true,
    chapter_filter: 'completed',
  });

  const fetchData = async () => {
    setLoading(true);
    try {
      const [projectsRes, formatsRes, historyRes] = await Promise.all([
        api.get("/projects/"),
        api.get("/export/formats"),
        api.get("/export/history"),
      ]);

      setProjects(projectsRes.data.projects || []);
      setFormats(formatsRes.data.formats || []);
      setHistory(historyRes.data.exports || []);

      if (projectsRes.data.projects?.length > 0 && !exportConfig.project_id) {
        setExportConfig(prev => ({
          ...prev,
          project_id: projectsRes.data.projects[0].id
        }));
        fetchStats(projectsRes.data.projects[0].id);
      }
    } catch (err) {
      setError('获取数据失败: ' + err.message);
    }
    setLoading(false);
  };

  const fetchStats = async (projectId) => {
    try {
      const res = await api.get(`/export/stats/word-count/${projectId}`);
      setStats(res.data);
    } catch (err) {
      console.error('获取统计失败:', err);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const downloadExport = async (filename) => {
    try {
      const response = await api.get(`/export/download/${filename}`, {
        responseType: 'blob',
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError('下载失败: ' + err.message);
    }
  };

  const handleExport = async () => {
    setLoading(true);
    try {
      const res = await api.post("/export/", exportConfig);
      setDialogOpen(false);
      fetchData();
      await downloadExport(res.data.filename);
    } catch (err) {
      setError(err.response?.data?.detail || '导出失败');
    }
    setLoading(false);
  };

  const handleDelete = async (filename) => {
    try {
      await api.delete(`/export/${filename}`);
      fetchData();
    } catch (err) {
      setError('删除失败: ' + err.message);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <div className="export-page">
      <h1 className="page-title">小说导出中心</h1>

      {error && (
        <div className="alert alert-error" onClick={() => setError(null)}>
          {error}
        </div>
      )}

      <div className="stats-grid">
        <div className="stat-card">
          <h3>总章节数</h3>
          <div className="stat-value">{stats?.total_chapters || 0}</div>
        </div>
        <div className="stat-card">
          <h3>总字数</h3>
          <div className="stat-value">{(stats?.total_word_count || 0).toLocaleString()}</div>
        </div>
        <div className="stat-card">
          <h3>已完成字数</h3>
          <div className="stat-value success">{(stats?.completed_word_count || 0).toLocaleString()}</div>
        </div>
        <div className="stat-card">
          <h3>导出历史</h3>
          <div className="stat-value">{history.length}</div>
        </div>
      </div>

      <div className="section-card">
        <div className="section-header">
          <h2>快速导出</h2>
          <button className="btn btn-primary" onClick={() => setDialogOpen(true)}>
            导出小说
          </button>
        </div>
        <div className="format-chips">
          {formats.map((fmt) => (
            <span
              key={fmt.id}
              className="chip"
              onClick={() => {
                setExportConfig(prev => ({ ...prev, format: fmt.id }));
                setDialogOpen(true);
              }}
            >
              {fmt.name}
            </span>
          ))}
        </div>
      </div>

      <div className="section-card">
        <h2>导出历史</h2>
        {history.length === 0 ? (
          <p className="empty-text">暂无导出记录</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>文件名</th>
                <th>格式</th>
                <th>大小</th>
                <th>时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {history.map((item) => (
                <tr key={item.filename}>
                  <td>{item.filename}</td>
                  <td><span className="badge">{item.format.toUpperCase()}</span></td>
                  <td>{formatFileSize(item.size)}</td>
                  <td>{new Date(item.created_at).toLocaleString()}</td>
                  <td>
                    <button className="btn btn-sm" onClick={() => downloadExport(item.filename)}>下载</button>
                    <button className="btn btn-danger btn-sm" onClick={() => handleDelete(item.filename)}>删除</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {dialogOpen && (
        <div className="modal-overlay" onClick={() => setDialogOpen(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h2>导出小说</h2>
            <div className="form-group">
              <label>选择项目</label>
              <select
                value={exportConfig.project_id}
                onChange={(e) => {
                  setExportConfig({ ...exportConfig, project_id: e.target.value });
                  fetchStats(e.target.value);
                }}
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>导出格式</label>
              <select
                value={exportConfig.format}
                onChange={(e) => setExportConfig({ ...exportConfig, format: e.target.value })}
              >
                {formats.map((fmt) => (
                  <option key={fmt.id} value={fmt.id}>{fmt.name}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>章节范围</label>
              <select
                value={exportConfig.chapter_filter}
                onChange={(e) => setExportConfig({ ...exportConfig, chapter_filter: e.target.value })}
              >
                <option value="completed">仅已完成</option>
                <option value="reviewed">已完成和审核中</option>
                <option value="all">全部章节</option>
              </select>
            </div>
            <div className="form-group checkbox">
              <label>
                <input
                  type="checkbox"
                  checked={exportConfig.include_outline}
                  onChange={(e) => setExportConfig({ ...exportConfig, include_outline: e.target.checked })}
                />
                包含大纲
              </label>
            </div>
            <div className="form-group checkbox">
              <label>
                <input
                  type="checkbox"
                  checked={exportConfig.include_metadata}
                  onChange={(e) => setExportConfig({ ...exportConfig, include_metadata: e.target.checked })}
                />
                包含元数据
              </label>
            </div>
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setDialogOpen(false)}>取消</button>
              <button className="btn btn-primary" onClick={handleExport} disabled={loading}>
                {loading ? '导出中...' : '导出'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ExportPage;

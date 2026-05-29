import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Chip,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Checkbox,
  List,
  ListItem,
  ListItemText,
  IconButton,
  Alert,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tooltip,
} from '@mui/material';
import {
  Download,
  Delete,
  Description,
  TextSnippet,
  PictureAsPdf,
  Book,
  DataObject,
  Article,
} from '@mui/icons-material';

import api from "../services/api";

const formatIcons = {
  md: <Article />,
  txt: <TextSnippet />,
  docx: <Description />,
  epub: <Book />,
  pdf: <PictureAsPdf />,
  json: <DataObject />,
};

const formatColors = {
  md: 'primary',
  txt: 'default',
  docx: 'info',
  epub: 'warning',
  pdf: 'error',
  json: 'success',
};

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

  // 使用 axios blob 下载文件（携带 X-API-Key）
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
      // 自动下载 - 使用 axios blob
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

  const handleDownload = async (filename) => {
    await downloadExport(filename);
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        小说导出中心
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* 统计卡片 */}
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                总章节数
              </Typography>
              <Typography variant="h4">
                {stats?.total_chapters || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                总字数
              </Typography>
              <Typography variant="h4">
                {(stats?.total_word_count || 0).toLocaleString()}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                已完成字数
              </Typography>
              <Typography variant="h4" color="success.main">
                {(stats?.completed_word_count || 0).toLocaleString()}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                导出历史
              </Typography>
              <Typography variant="h4">
                {history.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* 导出按钮 */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Typography variant="h6">快速导出</Typography>
                <Button
                  variant="contained"
                  startIcon={<Download />}
                  onClick={() => setDialogOpen(true)}
                >
                  导出小说
                </Button>
              </Box>

              <Box mt={2} display="flex" gap={1} flexWrap="wrap">
                {formats.map((fmt) => (
                  <Chip
                    key={fmt.id}
                    icon={formatIcons[fmt.id]}
                    label={fmt.name}
                    color={formatColors[fmt.id]}
                    variant="outlined"
                    onClick={() => {
                      setExportConfig(prev => ({ ...prev, format: fmt.id }));
                      setDialogOpen(true);
                    }}
                    sx={{ cursor: 'pointer' }}
                  />
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* 导出历史 */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                导出历史
              </Typography>

              {history.length === 0 ? (
                <Typography color="text.secondary" align="center" py={3}>
                  暂无导出记录
                </Typography>
              ) : (
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>文件名</TableCell>
                      <TableCell>格式</TableCell>
                      <TableCell>大小</TableCell>
                      <TableCell>时间</TableCell>
                      <TableCell>操作</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {history.map((item) => (
                      <TableRow key={item.filename}>
                        <TableCell>{item.filename}</TableCell>
                        <TableCell>
                          <Chip
                            size="small"
                            icon={formatIcons[item.format]}
                            label={item.format.toUpperCase()}
                            color={formatColors[item.format] || 'default'}
                          />
                        </TableCell>
                        <TableCell>{formatFileSize(item.size)}</TableCell>
                        <TableCell>
                          {new Date(item.created_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <Tooltip title="下载">
                            <IconButton
                              size="small"
                              onClick={() => handleDownload(item.filename)}
                            >
                              <Download />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="删除">
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => handleDelete(item.filename)}
                            >
                              <Delete />
                            </IconButton>
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* 导出对话框 */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>导出小说</DialogTitle>
        <DialogContent>
          <FormControl fullWidth sx={{ mt: 2, mb: 2 }}>
            <InputLabel>选择项目</InputLabel>
            <Select
              value={exportConfig.project_id}
              onChange={(e) => {
                setExportConfig({ ...exportConfig, project_id: e.target.value });
                fetchStats(e.target.value);
              }}
            >
              {projects.map((p) => (
                <MenuItem key={p.id} value={p.id}>
                  {p.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>导出格式</InputLabel>
            <Select
              value={exportConfig.format}
              onChange={(e) => setExportConfig({ ...exportConfig, format: e.target.value })}
            >
              {formats.map((fmt) => (
                <MenuItem key={fmt.id} value={fmt.id}>
                  {formatIcons[fmt.id]}
                  {fmt.name} - {fmt.description}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>章节范围</InputLabel>
            <Select
              value={exportConfig.chapter_filter}
              onChange={(e) => setExportConfig({ ...exportConfig, chapter_filter: e.target.value })}
            >
              <MenuItem value="completed">仅已完成</MenuItem>
              <MenuItem value="reviewed">已完成和审核中</MenuItem>
              <MenuItem value="all">全部章节</MenuItem>
            </Select>
          </FormControl>

          <FormControlLabel
            control={
              <Checkbox
                checked={exportConfig.include_outline}
                onChange={(e) => setExportConfig({ ...exportConfig, include_outline: e.target.checked })}
              />
            }
            label="包含大纲"
          />

          <FormControlLabel
            control={
              <Checkbox
                checked={exportConfig.include_metadata}
                onChange={(e) => setExportConfig({ ...exportConfig, include_metadata: e.target.checked })}
              />
            }
            label="包含元数据"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>取消</Button>
          <Button onClick={handleExport} variant="contained" disabled={loading}>
            {loading ? '导出中...' : '导出'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default ExportPage;

import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  Grid,
  LinearProgress,
  Chip,
  Alert,
  List,
  ListItem,
  ListItemText,
  Divider,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  PlayArrow,
  Stop,
  Pause,
  Refresh,
  Delete,
  Add,
  TrendingUp,
  Schedule,
} from '@mui/icons-material';

const API_BASE = 'http://localhost:8000';

const statusMap = {
  idle: { label: '空闲', color: 'default' },
  running: { label: '运行中', color: 'success' },
  paused: { label: '已暂停', color: 'warning' },
  stopped: { label: '已停止', color: 'error' },
};

function WorkerDashboard() {
  const [workerStatus, setWorkerStatus] = useState(null);
  const [queueStatus, setQueueStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [confirmDialog, setConfirmDialog] = useState({ open: false, action: '' });

  const fetchStatus = async () => {
    try {
      const [workerRes, queueRes] = await Promise.all([
        fetch(`${API_BASE}/api/worker/stats`),
        fetch(`${API_BASE}/api/worker/queue/status`),
      ]);

      const workerData = await workerRes.json();
      const queueData = await queueRes.json();

      setWorkerStatus(workerData.worker);
      setQueueStatus(queueData);
    } catch (err) {
      setError('获取状态失败: ' + err.message);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const controlWorker = async (action) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/worker/control`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });
      const data = await res.json();
      setWorkerStatus((prev) => ({ ...prev, status: data.status }));
    } catch (err) {
      setError('操作失败: ' + err.message);
    }
    setLoading(false);
    setConfirmDialog({ open: false, action: '' });
  };

  const resetStats = async () => {
    try {
      await fetch(`${API_BASE}/api/worker/reset-stats`, { method: 'POST' });
      fetchStatus();
    } catch (err) {
      setError('重置失败: ' + err.message);
    }
  };

  const handleConfirm = (action) => {
    setConfirmDialog({ open: true, action });
  };

  const confirmAction = () => {
    controlWorker(confirmDialog.action);
  };

  const formatTime = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return `${hours}小时 ${mins}分钟`;
  };

  if (!workerStatus || !queueStatus) {
    return <LinearProgress />;
  }

  const status = statusMap[workerStatus.status] || statusMap.idle;
  const progress = queueStatus.progress || { percentage: 0, completed: 0, total: 0 };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        24小时自动写作控制台
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Worker 控制面板 */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Worker 状态
              </Typography>
              <Box sx={{ mb: 2 }}>
                <Chip
                  label={status.label}
                  color={status.color}
                  size="large"
                  sx={{ fontSize: '1.1rem', py: 1 }}
                />
              </Box>

              <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                {workerStatus.status === 'stopped' ? (
                  <Button
                    variant="contained"
                    color="success"
                    startIcon={<PlayArrow />}
                    onClick={() => handleConfirm('start')}
                    disabled={loading}
                  >
                    启动
                  </Button>
                ) : (
                  <>
                    <Button
                      variant="contained"
                      color="error"
                      startIcon={<Stop />}
                      onClick={() => handleConfirm('stop')}
                      disabled={loading}
                    >
                      停止
                    </Button>
                    {workerStatus.status === 'running' ? (
                      <Button
                        variant="outlined"
                        startIcon={<Pause />}
                        onClick={() => handleConfirm('pause')}
                        disabled={loading}
                      >
                        暂停
                      </Button>
                    ) : (
                      <Button
                        variant="outlined"
                        startIcon={<PlayArrow />}
                        onClick={() => handleConfirm('resume')}
                        disabled={loading}
                      >
                        恢复
                      </Button>
                    )}
                  </>
                )}
              </Box>

              {workerStatus.current_task && (
                <Alert severity="info" sx={{ mt: 2 }}>
                  <Typography variant="body2">
                    正在写作: {workerStatus.current_task.chapter_title}
                  </Typography>
                </Alert>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* 每日统计 */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                今日统计
              </Typography>
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  已完成章节
                </Typography>
                <Typography variant="h4">
                  {workerStatus.daily_stats.chapters_completed}
                </Typography>
              </Box>
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  已写字数
                </Typography>
                <Typography variant="h4">
                  {workerStatus.daily_stats.words_written.toLocaleString()}
                </Typography>
              </Box>
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Token 消耗
                </Typography>
                <Typography variant="h4">
                  {workerStatus.daily_stats.tokens_used.toLocaleString()}
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                运行时间: {formatTime(workerStatus.uptime)}
              </Typography>
              <Button
                size="small"
                startIcon={<Refresh />}
                onClick={resetStats}
                sx={{ mt: 1 }}
              >
                重置统计
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* 队列状态 */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                写作队列
              </Typography>
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" gutterBottom>
                  总体进度
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={progress.percentage}
                  sx={{ height: 10, borderRadius: 5 }}
                />
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  {progress.completed} / {progress.total} ({progress.percentage.toFixed(1)}%)
                </Typography>
              </Box>

              <List dense>
                <ListItem>
                  <ListItemText
                    primary="待写作"
                    secondary={queueStatus.pending}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="写作中"
                    secondary={queueStatus.writing}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="审核中"
                    secondary={queueStatus.review}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="已完成"
                    secondary={queueStatus.completed}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="失败"
                    secondary={queueStatus.failed}
                  />
                </ListItem>
              </List>
            </CardContent>
          </Card>
        </Grid>

        {/* 操作提示 */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                使用说明
              </Typography>
              <Typography variant="body2" color="text.secondary">
                1. 点击"启动"开始 24 小时自动写作循环<br />
                2. Worker 会自动从队列中获取待写作章节<br />
                3. 完成一章后自动开始下一章<br />
                4. 达到每日字数或 Token 预算后自动暂停<br />
                5. 可以在项目设置中配置每日目标
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* 确认对话框 */}
      <Dialog open={confirmDialog.open} onClose={() => setConfirmDialog({ open: false, action: '' })}>
        <DialogTitle>确认操作</DialogTitle>
        <DialogContent>
          <Typography>
            确定要{confirmDialog.action === 'start' ? '启动' : confirmDialog.action === 'stop' ? '停止' : confirmDialog.action === 'pause' ? '暂停' : '恢复'} Worker 吗？
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDialog({ open: false, action: '' })}>
            取消
          </Button>
          <Button onClick={confirmAction} variant="contained" color="primary">
            确认
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default WorkerDashboard;

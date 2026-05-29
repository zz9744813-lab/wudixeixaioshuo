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
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  List,
  ListItem,
  ListItemText,
  IconButton,
  Alert,
  LinearProgress,
  Tabs,
  Tab,
} from '@mui/material';
import {
  CheckCircle,
  Error,
  Warning,
  Info,
  TrendingUp,
  Add,
} from '@mui/icons-material';
import api from '../services/api';

const severityColors = {
  low: 'success',
  medium: 'warning',
  high: 'error',
  critical: 'error',
};

const categoryLabels = {
  content: '内容',
  style: '风格',
  grammar: '语法',
  continuity: '连贯性',
  engagement: '吸引力',
};

function FeedbackCenter() {
  const [activeTab, setActiveTab] = useState(0);
  const [feedbacks, setFeedbacks] = useState([]);
  const [stats, setStats] = useState(null);
  const [trend, setTrend] = useState([]);
  const [issues, setIssues] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [newFeedback, setNewFeedback] = useState({
    project_id: 1,
    category: 'content',
    severity: 'medium',
    content: '',
  });

  const fetchData = async () => {
    setLoading(true);
    try {
      const [fbRes, statsRes, issuesRes] = await Promise.all([
        api.get('/feedback/?limit=50'),
        api.get('/feedback/stats/overview'),
        api.get('/feedback/issues/common?limit=10'),
      ]);

      setFeedbacks(fbRes.data.items || []);
      setStats(statsRes.data);
      setIssues(issuesRes.data.issues || []);
    } catch (err) {
      setError('获取数据失败: ' + err.message);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSubmitFeedback = async () => {
    try {
      await api.post('/feedback/', newFeedback);
      setDialogOpen(false);
      setNewFeedback({ ...newFeedback, content: '' });
      fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || '提交失败');
    }
  };

  const handleResolve = async (id) => {
    try {
      await api.post(`/feedback/${id}/resolve`, { resolution: '已手动解决' });
      fetchData();
    } catch (err) {
      setError('操作失败: ' + err.message);
    }
  };
      setError('解决失败: ' + err.message);
    }
  };

  const renderStats = () => {
    if (!stats) return <LinearProgress />;

    return (
      <Grid container spacing={3}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                总反馈数
              </Typography>
              <Typography variant="h4">{stats.total}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                已解决
              </Typography>
              <Typography variant="h4" color="success.main">
                {stats.resolved}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                待处理
              </Typography>
              <Typography variant="h4" color="warning.main">
                {stats.unresolved}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                解决率
              </Typography>
              <Typography variant="h4">{stats.resolution_rate}%</Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* 维度平均分 */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                各维度平均分
              </Typography>
              <Grid container spacing={2}>
                {Object.entries(stats.average_scores || {}).map(([dim, score]) => (
                  <Grid item xs={6} md={2} key={dim}>
                    <Box textAlign="center">
                      <Typography variant="body2" color="text.secondary">
                        {dim}
                      </Typography>
                      <Typography
                        variant="h5"
                        color={score >= 7 ? 'success.main' : score >= 5 ? 'warning.main' : 'error.main'}
                      >
                        {score}
                      </Typography>
                    </Box>
                  </Grid>
                ))}
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    );
  };

  const renderFeedbackList = () => (
    <Card>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6">反馈列表</Typography>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => setDialogOpen(true)}
          >
            提交反馈
          </Button>
        </Box>

        <List>
          {feedbacks.map((fb) => (
            <ListItem
              key={fb.id}
              divider
              secondaryAction={
                !fb.is_resolved && (
                  <Button
                    size="small"
                    startIcon={<CheckCircle />}
                    onClick={() => handleResolve(fb.id)}
                  >
                    解决
                  </Button>
                )
              }
            >
              <ListItemText
                primary={
                  <Box display="flex" alignItems="center" gap={1}>
                    <Chip
                      size="small"
                      label={categoryLabels[fb.category] || fb.category}
                      color="primary"
                      variant="outlined"
                    />
                    <Chip
                      size="small"
                      label={fb.severity}
                      color={severityColors[fb.severity] || 'default'}
                    />
                    {fb.is_resolved && (
                      <Chip size="small" label="已解决" color="success" />
                    )}
                  </Box>
                }
                secondary={
                  <>
                    <Typography variant="body2" component="span">
                      {fb.content}
                    </Typography>
                    <br />
                    <Typography variant="caption" color="text.secondary">
                      {new Date(fb.created_at).toLocaleString()}
                    </Typography>
                  </>
                }
              />
            </ListItem>
          ))}
        </List>
      </CardContent>
    </Card>
  );

  const renderCommonIssues = () => (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          常见问题
        </Typography>
        <List>
          {issues.map((issue, index) => (
            <ListItem key={issue.id} divider>
              <ListItemText
                primary={
                  <Box display="flex" alignItems="center" gap={1}>
                    <Typography variant="body1">
                      {index + 1}. {issue.content}
                    </Typography>
                    <Chip
                      size="small"
                      label={issue.severity}
                      color={severityColors[issue.severity] || 'default'}
                    />
                  </Box>
                }
                secondary={`类别: ${categoryLabels[issue.category] || issue.category}`}
              />
            </ListItem>
          ))}
        </List>
      </CardContent>
    </Card>
  );

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        反馈中心
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Tabs
        value={activeTab}
        onChange={(e, v) => setActiveTab(v)}
        sx={{ mb: 2 }}
      >
        <Tab label="统计概览" />
        <Tab label="反馈列表" />
        <Tab label="常见问题" />
      </Tabs>

      {activeTab === 0 && renderStats()}
      {activeTab === 1 && renderFeedbackList()}
      {activeTab === 2 && renderCommonIssues()}

      {/* 提交反馈对话框 */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>提交反馈</DialogTitle>
        <DialogContent>
          <FormControl fullWidth sx={{ mt: 2, mb: 2 }}>
            <InputLabel>类别</InputLabel>
            <Select
              value={newFeedback.category}
              onChange={(e) => setNewFeedback({ ...newFeedback, category: e.target.value })}
            >
              <MenuItem value="content">内容</MenuItem>
              <MenuItem value="style">风格</MenuItem>
              <MenuItem value="grammar">语法</MenuItem>
              <MenuItem value="continuity">连贯性</MenuItem>
              <MenuItem value="engagement">吸引力</MenuItem>
            </Select>
          </FormControl>

          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>严重程度</InputLabel>
            <Select
              value={newFeedback.severity}
              onChange={(e) => setNewFeedback({ ...newFeedback, severity: e.target.value })}
            >
              <MenuItem value="low">低</MenuItem>
              <MenuItem value="medium">中</MenuItem>
              <MenuItem value="high">高</MenuItem>
              <MenuItem value="critical">严重</MenuItem>
            </Select>
          </FormControl>

          <TextField
            fullWidth
            multiline
            rows={4}
            label="反馈内容"
            value={newFeedback.content}
            onChange={(e) => setNewFeedback({ ...newFeedback, content: e.target.value })}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>取消</Button>
          <Button onClick={handleSubmitFeedback} variant="contained">
            提交
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default FeedbackCenter;

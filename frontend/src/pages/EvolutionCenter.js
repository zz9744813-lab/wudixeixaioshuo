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
  Stepper,
  Step,
  StepLabel,
  Alert,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
} from '@mui/material';
import {
  PlayArrow,
  CheckCircle,
  Error,
  RotateLeft,
  Science,
  TrendingUp,
} from '@mui/icons-material';

const API_BASE = 'http://localhost:8000';

const statusColors = {
  evaluating: 'info',
  testing: 'warning',
  completed: 'success',
  rolled_back: 'error',
};

const statusLabels = {
  evaluating: '评估中',
  testing: '测试中',
  completed: '已完成',
  rolled_back: '已回滚',
};

function EvolutionCenter() {
  const [evolutions, setEvolutions] = useState([]);
  const [stats, setStats] = useState(null);
  const [practices, setPractices] = useState([]);
  const [dimensions, setDimensions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [selectedEvolution, setSelectedEvolution] = useState(null);
  const [activeStep, setActiveStep] = useState(0);
  const [newEvolution, setNewEvolution] = useState({
    project_id: 1,
    target_dimension: 'plot',
    strategy: 'auto',
    prompt_type: 'writing',
  });

  const steps = ['评估反馈', '生成改进', 'A/B测试', '决策应用'];

  const fetchData = async () => {
    setLoading(true);
    try {
      const [evoRes, statsRes, practicesRes, dimRes] = await Promise.all([
        fetch(`${API_BASE}/api/evolution/`),
        fetch(`${API_BASE}/api/evolution/stats/overview`),
        fetch(`${API_BASE}/api/evolution/best-practices`),
        fetch(`${API_BASE}/api/evolution/dimensions`),
      ]);

      const evoData = await evoRes.json();
      const statsData = await statsRes.json();
      const practicesData = await practicesRes.json();
      const dimData = await dimRes.json();

      setEvolutions(evoData.items || []);
      setStats(statsData);
      setPractices(practicesData.practices || []);
      setDimensions(dimData.dimensions || []);
    } catch (err) {
      setError('获取数据失败: ' + err.message);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreateEvolution = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/evolution/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newEvolution),
      });

      if (res.ok) {
        setDialogOpen(false);
        fetchData();
      } else {
        const err = await res.json();
        setError(err.detail || '创建失败');
      }
    } catch (err) {
      setError('创建失败: ' + err.message);
    }
  };

  const handleAction = async (id, action) => {
    try {
      const res = await fetch(`${API_BASE}/api/evolution/${id}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });

      if (res.ok) {
        fetchData();
        if (detailOpen) setDetailOpen(false);
      } else {
        const err = await res.json();
        setError(err.detail || '操作失败');
      }
    } catch (err) {
      setError('操作失败: ' + err.message);
    }
  };

  const viewDetail = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/api/evolution/${id}`);
      const data = await res.json();
      setSelectedEvolution(data);
      setDetailOpen(true);

      // 根据状态设置步骤
      if (data.status === 'evaluating') setActiveStep(0);
      else if (data.status === 'testing') setActiveStep(2);
      else setActiveStep(3);
    } catch (err) {
      setError('获取详情失败: ' + err.message);
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
                总进化轮次
              </Typography>
              <Typography variant="h4">{stats.total_evolutions}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                成功应用
              </Typography>
              <Typography variant="h4" color="success.main">
                {stats.completed}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                已回滚
              </Typography>
              <Typography variant="h4" color="error.main">
                {stats.rolled_back}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                成功率
              </Typography>
              <Typography variant="h4">{stats.success_rate}%</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    );
  };

  const renderEvolutionList = () => (
    <Card>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6">进化记录</Typography>
          <Button
            variant="contained"
            startIcon={<Science />}
            onClick={() => setDialogOpen(true)}
          >
            开始新进化
          </Button>
        </Box>

        <Table>
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>目标维度</TableCell>
              <TableCell>策略</TableCell>
              <TableCell>状态</TableCell>
              <TableCell>创建时间</TableCell>
              <TableCell>操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {evolutions.map((evo) => (
              <TableRow key={evo.id}>
                <TableCell>{evo.id}</TableCell>
                <TableCell>{evo.target_dimension}</TableCell>
                <TableCell>{evo.strategy}</TableCell>
                <TableCell>
                  <Chip
                    size="small"
                    label={statusLabels[evo.status] || evo.status}
                    color={statusColors[evo.status] || 'default'}
                  />
                </TableCell>
                <TableCell>
                  {new Date(evo.created_at).toLocaleDateString()}
                </TableCell>
                <TableCell>
                  <Button
                    size="small"
                    onClick={() => viewDetail(evo.id)}
                  >
                    详情
                  </Button>
                  {evo.status === 'completed' && (
                    <Button
                      size="small"
                      color="error"
                      onClick={() => handleAction(evo.id, 'rollback')}
                    >
                      回滚
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );

  const renderBestPractices = () => (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          最佳实践
        </Typography>
        <List>
          {practices.map((practice, index) => (
            <ListItem key={index} divider>
              <ListItemText
                primary={
                  <Box display="flex" alignItems="center" gap={1}>
                    <Chip
                      size="small"
                      label={practice.dimension}
                      color="primary"
                      variant="outlined"
                    />
                    <Typography variant="body1">
                      {practice.strategy} 策略
                    </Typography>
                  </Box>
                }
                secondary={practice.changes}
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
        Darwin 进化中心
      </Typography>
      <Typography variant="body1" color="text.secondary" gutterBottom>
        学习反馈 → 改进提示词 → 测试效果 → 保留/回滚
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {renderStats()}

      <Box mt={3}>
        {renderEvolutionList()}
      </Box>

      <Box mt={3}>
        {renderBestPractices()}
      </Box>

      {/* 创建进化对话框 */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>开始新进化</DialogTitle>
        <DialogContent>
          <FormControl fullWidth sx={{ mt: 2, mb: 2 }}>
            <InputLabel>目标维度</InputLabel>
            <Select
              value={newEvolution.target_dimension}
              onChange={(e) => setNewEvolution({ ...newEvolution, target_dimension: e.target.value })}
            >
              {dimensions.map((dim) => (
                <MenuItem key={dim.id} value={dim.id}>
                  {dim.name} - {dim.description}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>策略</InputLabel>
            <Select
              value={newEvolution.strategy}
              onChange={(e) => setNewEvolution({ ...newEvolution, strategy: e.target.value })}
            >
              <MenuItem value="auto">自动</MenuItem>
              <MenuItem value="conservative">保守</MenuItem>
              <MenuItem value="aggressive">激进</MenuItem>
              <MenuItem value="targeted">针对性</MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>取消</Button>
          <Button onClick={handleCreateEvolution} variant="contained">
            开始进化
          </Button>
        </DialogActions>
      </Dialog>

      {/* 详情对话框 */}
      <Dialog
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          进化详情 #{selectedEvolution?.id}
        </DialogTitle>
        <DialogContent>
          {selectedEvolution && (
            <>
              <Stepper activeStep={activeStep} sx={{ mb: 3 }}>
                {steps.map((label) => (
                  <Step key={label}>
                    <StepLabel>{label}</StepLabel>
                  </Step>
                ))}
              </Stepper>

              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="subtitle2">目标维度</Typography>
                  <Typography>{selectedEvolution.target_dimension}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="subtitle2">策略</Typography>
                  <Typography>{selectedEvolution.strategy}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="subtitle2">状态</Typography>
                  <Chip
                    size="small"
                    label={statusLabels[selectedEvolution.status] || selectedEvolution.status}
                    color={statusColors[selectedEvolution.status] || 'default'}
                  />
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="subtitle2">假设</Typography>
                  <Typography>{selectedEvolution.hypothesis}</Typography>
                </Grid>
              </Grid>

              {selectedEvolution.versions?.length > 0 && (
                <Box mt={3}>
                  <Typography variant="h6" gutterBottom>
                    版本历史
                  </Typography>
                  {selectedEvolution.versions.map((v) => (
                    <Card key={v.id} variant="outlined" sx={{ mb: 1 }}>
                      <CardContent>
                        <Typography variant="subtitle2">
                          版本 {v.version_number}
                          {v.is_active && (
                            <Chip size="small" label="当前激活" color="success" sx={{ ml: 1 }} />
                          )}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {v.changes_summary}
                        </Typography>
                      </CardContent>
                    </Card>
                  ))}
                </Box>
              )}
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailOpen(false)}>关闭</Button>
          {selectedEvolution?.status === 'testing' && (
            <Button
              variant="contained"
              color="success"
              onClick={() => handleAction(selectedEvolution.id, 'apply')}
            >
              应用进化
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default EvolutionCenter;

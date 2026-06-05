import React, { useCallback, useEffect, useState } from 'react';
import api from '../services/api';
import { useToast } from '../contexts/ToastContext';
import { Icon } from '../components/ui/Icon';
import { AsyncState } from '../components/ui/AsyncState';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { toArray } from '../utils/nullSafety';

import PageHeader from '../components/console/PageHeader';
import MetricCard from '../components/console/MetricCard';
import SectionCard from '../components/console/SectionCard';
import styles from './ReviewCommentsPage.module.css';

const PAGE_TITLE = '💬 作品评论区';
const PAGE_SUBTITLE = '5 个模拟读者 Agent + 主 Agent 自动接入';

const STATUS_VARIANT = {
  new: 'accent',
  replied: 'info',
  grouped: 'warning',
  discussing: 'warning',
  accepted: 'success',
  rejected: 'danger',
  ignored: 'muted',
  done: 'muted',
};

const AUTHOR_VARIANT = {
  user: 'primary',
  reader_agent: 'warning',
  chief_agent: 'success',
  system: 'muted',
};

const SEVERITY_VARIANT = {
  low: 'muted',
  medium: 'info',
  high: 'warning',
  blocker: 'danger',
};

const DEFAULT_FORM = { content: '', tags: '' };

export default function ReviewCommentsPage() {
  const toast = useToast();
  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [comments, setComments] = useState([]);
  const [groups, setGroups] = useState([]);
  const [profiles, setProfiles] = useState([]);
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [form, setForm] = useState(DEFAULT_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [filterStatus, setFilterStatus] = useState('');
  const [filterAuthor, setFilterAuthor] = useState('');

  const fetchProjects = useCallback(async () => {
    try {
      const res = await api.get('/projects/');
      setProjects(toArray(res.data));
    } catch (err) {
      // 静默
    }
  }, []);

  const fetchData = useCallback(async () => {
    if (!selectedProjectId) return;
    setLoading(true);
    setError('');
    try {
      const [commentsRes, groupsRes, profilesRes, settingsRes] = await Promise.all([
        api.get('/reviews/comments', { params: { project_id: selectedProjectId, limit: 50 } }),
        api.get('/reviews/groups', { params: { project_id: selectedProjectId } }),
        api.get('/reviews/reader-profiles'),
        api.get('/reviews/settings', { params: { project_id: selectedProjectId } }),
      ]);
      setComments(toArray(commentsRes.data?.items));
      setGroups(toArray(groupsRes.data));
      setProfiles(toArray(profilesRes.data));
      setSettings(settingsRes.data);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || '加载失败');
    } finally {
      setLoading(false);
    }
  }, [selectedProjectId]);

  useEffect(() => { fetchProjects(); }, [fetchProjects]);
  useEffect(() => { fetchData(); }, [fetchData]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.content.trim() || !selectedProjectId) {
      toast.error('请输入评论内容', 4000);
      return;
    }
    setSubmitting(true);
    try {
      const tags = form.tags
        .split(/[,，]/)
        .map((t) => t.trim())
        .filter(Boolean);
      await api.post('/reviews/comments', {
        project_id: Number(selectedProjectId),
        content: form.content,
        tags,
      });
      toast.success('已发表, 主 Agent 自动接入中');
      setForm(DEFAULT_FORM);
      fetchData();
    } catch (err) {
      toast.error(err?.response?.data?.detail || '发表失败', 5000);
    } finally {
      setSubmitting(false);
    }
  };

  const handleTriggerTriage = async () => {
    if (!selectedProjectId) return;
    try {
      const res = await api.post('/reviews/triage', null, {
        params: { project_id: selectedProjectId },
      });
      toast.success(`分流: ${res.data?.status} | handled=${res.data?.handled || 0}`);
      fetchData();
    } catch (err) {
      toast.error('分流失败', 5000);
    }
  };

  const handleTriggerCleanup = async () => {
    try {
      const res = await api.post('/reviews/cleanup', null, { params: { retention_days: 7 } });
      toast.success(`清理: 删 user=${res.data?.deleted_user} reader=${res.data?.deleted_reader}`);
      fetchData();
    } catch (err) {
      toast.error('清理失败', 5000);
    }
  };

  const filteredComments = comments.filter((c) => {
    if (filterStatus && c.status !== filterStatus) return false;
    if (filterAuthor && c.author_type !== filterAuthor) return false;
    return true;
  });

  const totalComments = comments.length;
  const userComments = comments.filter((c) => c.author_type === 'user').length;
  const readerComments = comments.filter((c) => c.author_type === 'reader_agent').length;
  const chiefReplies = comments.filter((c) => c.author_type === 'chief_agent').length;
  const newComments = comments.filter((c) => c.status === 'new').length;

  return (
    <div className={styles.page}>
      <PageHeader title={PAGE_TITLE} subtitle={PAGE_SUBTITLE} />

      <div className={styles.selectorRow}>
        <span className={styles.label}>项目:</span>
        <select
          className={styles.select}
          value={selectedProjectId}
          onChange={(e) => setSelectedProjectId(e.target.value)}
        >
          <option value="">-- 请选择 --</option>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
        {selectedProjectId && (
          <>
            <Button variant="ghost" size="sm" onClick={handleTriggerTriage}>
              <Icon name="Bot" size={14} /> 主 Agent 接入
            </Button>
            <Button variant="ghost" size="sm" onClick={handleTriggerCleanup}>
              <Icon name="Trash2" size={14} /> 立即清理过期
            </Button>
          </>
        )}
      </div>

      <AsyncState
        loading={loading}
        error={error}
        onRetry={fetchData}
        emptyTitle="请选择项目"
        emptyHint="从上方下拉框选一个项目, 加载评论区"
        hideLoading
      >
        <div className={styles.metricsGrid}>
          <MetricCard label="总评论" value={totalComments} unit="条" status="info" />
          <MetricCard label="用户评论" value={userComments} unit="条" status="primary" />
          <MetricCard label="读者 Agent" value={readerComments} unit="条" status="warning" />
          <MetricCard label="主 Agent 回复" value={chiefReplies} unit="条" status="success" />
          <MetricCard label="待处理" value={newComments} unit="条" status={newComments > 0 ? 'danger' : 'muted'} />
        </div>

        {/* 读者权重 + 设置 */}
        <div className={styles.twoCol}>
          <SectionCard title="📊 读者权重" subtitle="被采纳 +0.08, 被驳回 -0.03, 范围 [0.5, 2.5]">
            <AsyncState isEmpty={!profiles.length} emptyTitle="暂无 reader profile">
              <div className={styles.profileList}>
                {profiles.map((p) => (
                  <div key={p.id} className={styles.profileItem}>
                    <div className={styles.profileHeader}>
                      <span className={styles.profileName}>{p.display_name}</span>
                      <Badge variant="muted">{p.reader_key}</Badge>
                    </div>
                    <div className={styles.profileMeta}>
                      <span>权重: <strong>{Number(p.weight || 1).toFixed(2)}</strong></span>
                      <span>采纳: {p.adopted_count}</span>
                      <span>驳回: {p.rejected_count}</span>
                      <span>生成: {p.generated_comment_count}</span>
                    </div>
                    <div className={styles.profileBar}>
                      <div
                        className={styles.profileBarFill}
                        style={{ width: `${Math.min(100, (p.weight / 2.5) * 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </AsyncState>
          </SectionCard>

          <SectionCard title="⚙️ 评论设置" subtitle="自动接入 + 7 天清理">
            {settings ? (
              <div className={styles.settingsList}>
                <div className={styles.settingItem}>
                  <span>自动触发读者评审</span>
                  <Badge variant={settings.auto_reader_review ? 'success' : 'muted'}>
                    {settings.auto_reader_review ? '开' : '关'}
                  </Badge>
                </div>
                <div className={styles.settingItem}>
                  <span>主 Agent 自动分流</span>
                  <Badge variant={settings.auto_chief_triage ? 'success' : 'muted'}>
                    {settings.auto_chief_triage ? '开' : '关'}
                  </Badge>
                </div>
                <div className={styles.settingItem}>
                  <span>自动建讨论室</span>
                  <Badge variant={settings.auto_discussion ? 'success' : 'muted'}>
                    {settings.auto_discussion ? '开' : '关'}
                  </Badge>
                </div>
                <div className={styles.settingItem}>
                  <span>评论保留天数</span>
                  <Badge variant="info">{settings.retention_days} 天</Badge>
                </div>
                <div className={styles.settingItem}>
                  <span>每章评论上限</span>
                  <Badge variant="info">{settings.max_comments_per_chapter}</Badge>
                </div>
                <div className={styles.settingItem}>
                  <span>触发讨论的最低严重度</span>
                  <Badge variant="warning">{settings.min_severity_for_discussion}</Badge>
                </div>
              </div>
            ) : (
              <p style={{ color: 'var(--text-muted)' }}>加载中...</p>
            )}
          </SectionCard>
        </div>

        {/* 发表评论 */}
        <SectionCard title="✍️ 我要评论" subtitle="发表后主 Agent 会自动接入">
          <form className={styles.form} onSubmit={handleSubmit}>
            <textarea
              className={styles.textarea}
              placeholder="说点什么... (例: 女主转变缺少可信触发点)"
              value={form.content}
              onChange={(e) => setForm({ ...form, content: e.target.value })}
              rows={3}
              disabled={!selectedProjectId}
            />
            <div className={styles.formRow}>
              <input
                className={styles.input}
                type="text"
                placeholder="标签 (逗号分隔, 例: 人物动机, 情绪递进)"
                value={form.tags}
                onChange={(e) => setForm({ ...form, tags: e.target.value })}
                disabled={!selectedProjectId}
              />
              <Button
                variant="primary"
                type="submit"
                disabled={!selectedProjectId || submitting || !form.content.trim()}
              >
                {submitting ? '发表中…' : '发表'}
              </Button>
            </div>
          </form>
        </SectionCard>

        {/* 过滤栏 */}
        <SectionCard
          title="💬 评论流"
          subtitle={`${filteredComments.length} / ${totalComments} 条`}
        >
          <div className={styles.filterBar}>
            <span className={styles.filterLabel}>状态:</span>
            <button
              className={`${styles.chip} ${!filterStatus ? styles.chipActive : ''}`}
              onClick={() => setFilterStatus('')}
            >全部</button>
            {['new', 'replied', 'grouped', 'discussing', 'accepted', 'rejected', 'ignored'].map((s) => (
              <button
                key={s}
                className={`${styles.chip} ${filterStatus === s ? styles.chipActive : ''}`}
                onClick={() => setFilterStatus(s)}
              >{s}</button>
            ))}
            <span className={styles.filterLabel} style={{ marginLeft: 16 }}>作者:</span>
            <button
              className={`${styles.chip} ${!filterAuthor ? styles.chipActive : ''}`}
              onClick={() => setFilterAuthor('')}
            >全部</button>
            {['user', 'reader_agent', 'chief_agent'].map((a) => (
              <button
                key={a}
                className={`${styles.chip} ${filterAuthor === a ? styles.chipActive : ''}`}
                onClick={() => setFilterAuthor(a)}
              >{a}</button>
            ))}
          </div>

          <AsyncState isEmpty={!filteredComments.length} emptyTitle="暂无评论" emptyHint="选个项目然后发表一条, 或触发读者评审">
            <div className={styles.commentList}>
              {filteredComments.map((c) => (
                <div key={c.id} className={styles.commentCard}>
                  <div className={styles.commentHeader}>
                    <div className={styles.commentAuthor}>
                      <Badge variant={AUTHOR_VARIANT[c.author_type] || 'muted'}>
                        {c.author_label || c.author_type}
                      </Badge>
                      {c.chapter_id && (
                        <span className={styles.commentTarget}>第 {c.chapter_id} 章</span>
                      )}
                      <Badge variant={STATUS_VARIANT[c.status] || 'muted'}>
                        {c.status}
                      </Badge>
                      {c.priority >= 80 && <Badge variant="danger">高优</Badge>}
                    </div>
                    <span className={styles.commentTime}>
                      {c.created_at ? new Date(c.created_at).toLocaleString('zh-CN') : ''}
                    </span>
                  </div>
                  <p className={styles.commentContent}>{c.content}</p>
                  {Array.isArray(c.tags) && c.tags.length > 0 && (
                    <div className={styles.tagList}>
                      {c.tags.map((t) => <span key={t} className={styles.tag}>#{t}</span>)}
                    </div>
                  )}
                  {c.rating && c.rating.score != null && (
                    <div className={styles.rating}>
                      评分: <strong>{c.rating.score}</strong>
                    </div>
                  )}
                  {Array.isArray(c.replies) && c.replies.length > 0 && (
                    <div className={styles.replies}>
                      {c.replies.map((r) => (
                        <div key={r.id} className={styles.replyItem}>
                          <Badge variant="success" size="sm">{r.author_label || '主 Agent'}</Badge>
                          <span className={styles.replyContent}>{r.content}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </AsyncState>
        </SectionCard>

        {/* 评论组 */}
        <SectionCard title="📦 评论组" subtitle={`${groups.length} 个合并问题包`}>
          <AsyncState isEmpty={!groups.length} emptyTitle="暂无评论组">
            <div className={styles.groupList}>
              {groups.map((g) => (
                <div key={g.id} className={styles.groupCard}>
                  <div className={styles.groupHeader}>
                    <span className={styles.groupTitle}>{g.title}</span>
                    <Badge variant={SEVERITY_VARIANT[g.severity] || 'muted'}>
                      {g.severity}
                    </Badge>
                    <Badge variant={STATUS_VARIANT[g.status] || 'muted'}>
                      {g.status}
                    </Badge>
                  </div>
                  {g.summary && <p className={styles.groupSummary}>{g.summary}</p>}
                  <div className={styles.groupMeta}>
                    <span>{(g.comment_ids || []).length} 条评论</span>
                    {g.discussion_session_id && (
                      <span>讨论 #{g.discussion_session_id}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </AsyncState>
        </SectionCard>
      </AsyncState>
    </div>
  );
}

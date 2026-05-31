import React from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { Icon } from '../components/ui/Icon';
import { AsyncState } from '../components/ui/AsyncState';
import { useFetch } from '../hooks/useFetch';
import { useToast } from '../contexts/ToastContext';
import api from '../services/api';
import styles from './ReaderTrainingPage.module.css';

const PAGE_TITLE = '真人训练营';
const PAGE_ICON = 'Users';

export default function ReaderTrainingPage() {
  const { projectId, chapterId } = useParams();
  const [searchParams] = useSearchParams();
  const pid = Number(searchParams.get('project_id') || projectId || 0);
  const cid = Number(searchParams.get('chapter_id') || chapterId || 0);
  const toast = useToast();

  // ---- Breakpoint state (declared first) ----
  const [showBp, setShowBp] = React.useState(() => {
    try {
      const raw = localStorage.getItem('reader_training:bp');
      return !!raw;
    } catch (_e) { return false; }
  });
  const [bpInfo, setBpInfo] = React.useState(null);

  // ---- Chapter fetch ----
  const chapterQuery = useFetch(pid && cid ? `/projects/${pid}/chapters/${cid}` : '', { auto: false });
  const [chapter, setChapter] = React.useState(null);

  // ---- Feedback form state ----
  const [readerScore, setReaderScore] = React.useState('');
  const [reaction, setReaction] = React.useState('');
  const [rawComment, setRawComment] = React.useState('');
  const [anchors, setAnchors] = React.useState([]);
  const [selectedText, setSelectedText] = React.useState('');
  const [showAnchorInput, setShowAnchorInput] = React.useState(false);
  const [anchorComment, setAnchorComment] = React.useState('');
  const [anchorType, setAnchorType] = React.useState('pacing');
  const [submitting, setSubmitting] = React.useState(false);
  const [submitError, setSubmitError] = React.useState(null);

  // ---- Chapter data effects ----
  React.useEffect(() => {
    if (pid && cid) { chapterQuery.reload(); }
  }, [pid, cid]);

  React.useEffect(() => {
    if (!chapterQuery.data) return;
    const raw = chapterQuery.data;
    const ch = raw.length ? raw[0] : raw;
    if (ch) setChapter(ch);
  }, [chapterQuery.data]);

  // ---- Breakpoint restore effect ----
  React.useEffect(() => {
    if (bpInfo) return;
    try {
      const raw = localStorage.getItem('reader_training:bp');
      if (!raw) return;
      const parsed = JSON.parse(raw);
      const el = document.querySelector("." + styles.textBody);
      if (el) {
        const t = requestAnimationFrame(() => requestAnimationFrame(() => {
          el.scrollTop = parsed.scrollTop || 0;
        }));
        return () => cancelAnimationFrame(t);
      }
      setBpInfo(parsed);
    } catch (_e) { /* ignore */ }
  }, [bpInfo]);

  const handleScrollSave = () => {
    const el = document.querySelector("." + styles.textBody);
    if (!el) return;
    const data = { scrollTop: el.scrollTop, at: Date.now() };
    try { localStorage.setItem('reader_training:bp', JSON.stringify(data)); } catch (_e) {}
    setBpInfo(data);
  };

  // ---- Handlers ----
  const handleTextSelect = () => {
    const selection = window.getSelection();
    const text = selection.toString().trim();
    if (text && text.length > 2) {
      setSelectedText(text);
      setShowAnchorInput(true);
    }
  };

  const handleAddAnchor = () => {
    if (!anchorComment.trim()) return;
    setAnchors((a) => [
      ...a,
      { quote: selectedText, comment: anchorComment.trim(), type: anchorType, para: a.length + 1 },
    ]);
    setAnchorComment('');
    setSelectedText('');
    setShowAnchorInput(false);
  };

  const handleRemoveAnchor = (index) => {
    setAnchors((a) => a.filter((_, i) => i !== index));
  };

  const handleSubmit = async () => {
    setSubmitError(null);
    if (!pid) { toast.error('请先选择项目', 4000); return; }
    const score = readerScore === '' ? null : Math.min(100, Math.max(0, Number(readerScore)));
    if (score === null && !anchors.length && !reaction && !rawComment.trim()) {
      toast.error('请至少填写评分、反应或评论', 4000); return;
    }
    setSubmitting(true);
    try {
      const res = await api.post('/reader-training/feedback', {
        project_id: pid,
        chapter_id: cid || undefined,
        reader_score: score,
        reaction: reaction || undefined,
        anchor: anchors.length ? anchors : undefined,
        raw_comment: rawComment.trim() || undefined,
      });
      toast.success(res.data?.message || '反馈已入队', 4000);
      setReaderScore('');
      setReaction('');
      setRawComment('');
      setAnchors([]);
      localStorage.removeItem('reader_training:bp');
      setBpInfo(null);
      setShowBp(false);
    } catch (e) {
      const msg = e?.response?.data?.detail || e?.response?.data?.message || '提交失败，请重试';
      setSubmitError(msg);
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleReactionClick = (r) => {
    setReaction(r);
    const label = r === 'hooked' ? '上头' : r === 'meh' ? '一般' : '弃书';
    toast.info(`反应已选择：${label}`, 2000);
  };

  const handleClearBreakpoint = () => {
    localStorage.removeItem('reader_training:bp');
    setBpInfo(null);
    setShowBp(false);
    toast.info('断点已清除', 2500);
  };

  // ---- Render guards ----
  if (chapterQuery.loading) {
    return <AsyncState loading error={null}><div /></AsyncState>;
  }

  if (!pid) {
    return (
      <div className={styles.page}>
        <header className={styles.header}>
          <h1 className={styles.title}><Icon name={PAGE_ICON} size={22} /><span>{PAGE_TITLE}</span></h1>
        </header>
        <div className={styles.empty}>请在导航中选择一个包含章节的项目开始训练。</div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}><Icon name={PAGE_ICON} size={22} /><span>{PAGE_TITLE}</span></h1>
        <div className={styles.badges}>
          <span className={styles.badge}>项目 {pid}</span>
          {cid ? <span className={styles.badge}>章节 {cid}</span> : null}
        </div>
        {bpInfo && (
          <div className={styles.bpBar}>
            <span className={styles.badge}>断点已保存 (scroll: {bpInfo.scrollTop}px)</span>
            <button type="button" className={styles.ghost} onClick={handleClearBreakpoint}>清除</button>
          </div>
        )}
      </header>

      <div className={styles.layout}>
        <section className={styles.readerArea}>
          <div className={styles.chapterHeader}>
            <h3>{chapter?.title ? `第 ${chapter.chapter_index} 章：${chapter.title}` : '章节试读'}</h3>
          </div>
          {(chapter?.content || chapter?.final_content || '') ? (
            <div className={styles.textBody} onMouseUp={handleTextSelect} onScroll={handleScrollSave}>
                  {(chapter?.content || chapter?.final_content || '').split('\n').map((p, i) => (
                <p key={i}>{p || '\u00A0'}</p>
              ))}
              {selectedText && showAnchorInput && (
                <div className={styles.anchorPopover}>
                  <div className={styles.anchorQuote}>"{selectedText.slice(0, 60)}{selectedText.length > 60 ? '…' : ''}"</div>
                  <textarea
                    value={anchorComment}
                    onChange={(e) => setAnchorComment(e.target.value)}
                    placeholder="你的批注（问题 / 建议）"
                    rows={3}
                  />
                  <div className={styles.anchorActions}>
                    <select value={anchorType} onChange={(e) => setAnchorType(e.target.value)}>
                      <option value="pacing">节奏</option>
                      <option value="character">人物</option>
                      <option value="hook">爽点/钩子</option>
                      <option value="emotion">情绪</option>
                      <option value="setting">设定</option>
                      <option value="other">其他</option>
                    </select>
                    <button type="button" onClick={handleAddAnchor}>添加批注</button>
                    <button type="button" className={styles.ghost} onClick={() => setShowAnchorInput(false)}>取消</button>
                  </div>
                </div>
              )}
              {anchors.length > 0 && (
                <div className={styles.anchorList}>
                  {anchors.map((a, i) => (
                    <div key={i} className={styles.anchorItem}>
                      <span className={styles.anchorType}>{a.type}</span>
                      <div className={styles.anchorBody}>
                        <div className={styles.anchorQuote}>"{a.quote.slice(0, 40)}…"</div>
                        <div>{a.comment}</div>
                      </div>
                      <button type="button" onClick={() => handleRemoveAnchor(i)}>×</button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className={styles.empty}>暂无章节内容，请先在项目管理中生成章节。</div>
          )}
        </section>

        <aside className={styles.sidePanel}>
          <section className={styles.card}>
            <h3>你的评分</h3>
            <div className={styles.row}>
              <label>总分（0-100）</label>
              <input
                type="number"
                min={0}
                max={100}
                value={readerScore}
                onChange={(e) => setReaderScore(e.target.value)}
                placeholder="78"
              />
            </div>
            <div className={styles.reactions}>
              {[
                { key: 'hooked', label: '上头', icon: 'Flame' },
                { key: 'meh', label: '一般', icon: 'Meh' },
                { key: 'dropped', label: '弃书', icon: 'TrendingDown' },
              ].map((item) => (
                <button
                  key={item.key}
                  type="button"
                  className={`${styles.reactionBtn} ${reaction === item.key ? styles.reactionActive : ''}`}
                  onClick={() => handleReactionClick(item.key)}
                >
                  <Icon name={item.icon} size={16} />
                  <span>{item.label}</span>
                </button>
              ))}
            </div>
          </section>

          <section className={styles.card}>
            <h3>评论</h3>
            <textarea
              value={rawComment}
              onChange={(e) => setRawComment(e.target.value)}
              placeholder="整体评价、问题与建议"
              rows={5}
            />
          </section>

          <button
            type="button"
            className={styles.submitBtn}
            onClick={handleSubmit}
            disabled={submitting}
          >
            {submitting ? '提交中…' : '提交反馈'}
          </button>
          {submitError ? (
            <div className={styles.hint}>{submitError}</div>
          ) : null}
        </aside>
      </div>
    </div>
  );
}

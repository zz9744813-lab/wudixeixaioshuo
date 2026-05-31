import React, { useState, useEffect } from 'react';
import { useFetch } from '../hooks/useFetch';
import { Icon } from '../components/ui/Icon';
import { AsyncState } from '../components/ui/AsyncState';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { StatCard } from '../components/ui/StatCard';
import Modal from '../components/ui/Modal';
import { Table } from '../components/ui/Table';
import api from '../services/api';
import { useToast } from '../contexts/ToastContext';
import styles from './BibleEditor.module.css';

const PAGE_TITLE = 'Bible 编辑器';
const PAGE_ICON = 'BookOpen';

const CHARACTER_ROLE_COLORS = { '主角': 'primary', '配角': 'accent', '反派': 'danger', '导师': 'success' };

export default function BibleEditor() {
  const toast = useToast();
  const [projectId, setProjectId] = useState('');
  const [bible, setBible] = useState(null);
  const [loadingBible, setLoadingBible] = useState(false);
  const [worldDraft, setWorldDraft] = useState('');
  const [loadingWorld, setLoadingWorld] = useState(false);
  const [detailId, setDetailId] = useState(null);
  const [detailData, setDetailData] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [showCharForm, setShowCharForm] = useState(false);
  const [charForm, setCharForm] = useState({ name: '', role: '配角', personality: '', abilities: '', notes: '' });
  const [submitting, setSubmitting] = useState(false);

  const { data: projects = [], loading: loadingProjects } = useFetch('/projects/');

  useEffect(() => {
    if (projects.length && !projectId) {
      setProjectId(String(projects[0]?.id));
    }
  }, [projects]);

  const fetchBible = async (pid) => {
    if (!pid) return;
    setLoadingBible(true);
    try {
      const res = await api.get(`/bible/projects/${pid}/bible`);
      setBible(res.data);
    } catch (err) {
      toast.error('加载圣经失败');
    } finally {
      setLoadingBible(false);
    }
  };

  useEffect(() => { fetchBible(projectId); }, [projectId]);

  const openDetail = async (charId) => {
    setDetailId(charId);
    setLoadingDetail(true);
    setDetailData(null);
    try {
      const res = await api.get(`/bible/projects/${projectId}/bible/characters`);
      const chars = Array.isArray(res.data.characters) ? res.data.characters : [];
      const found = chars.find((c) => c.id === charId || c.name === charId);
      setDetailData(found);
    } catch {
      toast.error('加载人物详情失败');
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleAddCharacter = async (e) => {
    e.preventDefault();
    if (!charForm.name) { toast.error('请输入人物名称'); return; }
    setSubmitting(true);
    try {
      await api.post(`/bible/projects/${projectId}/bible/characters`, charForm);
      toast.success('人物已添加');
      setShowCharForm(false);
      setCharForm({ name: '', role: '配角', personality: '', abilities: '', notes: '' });
      fetchBible(projectId);
    } catch {
      toast.error('添加失败', 6000);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteCharacter = async (charId) => {
    try {
      await api.delete(`/bible/projects/${projectId}/bible/characters/${charId}`);
      toast.success('人物已删除');
      fetchBible(projectId);
    } catch {
      toast.error('删除失败');
    }
  };

  const handleGenerateWorld = async () => {
    setLoadingWorld(true);
    try {
      const res = await api.post(`/bible/projects/${projectId}/bible/world-setting/generate`, {}, { params: { hint: worldDraft } });
      setBible((prev) => ({ ...prev, world_setting: res.data.content }));
      toast.success('世界观已生成');
    } catch {
      toast.error('生成失败', 6000);
    } finally {
      setLoadingWorld(false);
    }
  };

  const characters = Array.isArray(bible?.characters) ? bible.characters : [];
  const columns = [
    { key: 'name', label: '姓名', render: (v, row) => <span className={styles.charName}>{v}</span> },
    { key: 'role', label: '角色', render: (v) => <Badge variant={CHARACTER_ROLE_COLORS[v] || 'accent'}>{v}</Badge> },
    { key: 'personality', label: '性格' },
    { key: 'abilities', label: '能力' },
    { key: 'id', label: '操作', render: (v, row) => (
      <span className={styles.cellActions}>
        <Button variant="ghost" size="sm" onClick={() => openDetail(row.id || row.name)}>详情</Button>
        <Button variant="danger" size="sm" onClick={() => handleDeleteCharacter(row.id || row.name)}>删除</Button>
      </span>
    ) },
  ];

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}><Icon name={PAGE_ICON} size={22} /><span>{PAGE_TITLE}</span></h1>
      </header>

      <div className={styles.projectBar}>
        <span className={styles.filterLabel}>项目：</span>
        <select className={styles.select} value={projectId} onChange={(e) => setProjectId(e.target.value)}>
          <option value="">-- 选择项目 --</option>
          {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
      </div>

      <AsyncState loading={loadingProjects || loadingBible} error={null} isEmpty={!projectId} emptyTitle="请选择项目"
                  hideLoading hideError>
        <div className={styles.body}>
          <StatCard label="人物数量" value={characters.length} />
          <StatCard label="卷数" value={bible?.volume_outline?.length || 0} />
          <StatCard label="章节数" value={bible?.chapter_outline?.length || 0} />

          <section className={styles.section}>
            <h3 className={styles.sectionTitle}>世界观设定</h3>
            <AsyncState loading={loadingWorld} isEmpty={!bible?.world_setting} emptyTitle="暂无世界观设置"
                        hideLoading hideError>
              <pre className={styles.worldPreview}>{bible?.world_setting}</pre>
            </AsyncState>
            <div className={styles.worldActions}>
              <input
                className={styles.input}
                placeholder="添加提示或关键词（可选）"
                value={worldDraft}
                onChange={(e) => setWorldDraft(e.target.value)}
              />
              <Button variant="primary" size="sm" onClick={handleGenerateWorld} loading={loadingWorld} disabled={!projectId}>
                AI 生成世界观
              </Button>
            </div>
          </section>

          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <h3 className={styles.sectionTitle}>人物列表</h3>
              <Button variant="primary" size="sm" onClick={() => setShowCharForm(true)}>+ 添加人物</Button>
            </div>
            <AsyncState loading={loadingBible} isEmpty={!characters.length} emptyTitle="暂无人物，先从书籍导入或手动添加"
                        hideLoading hideError>
              <Table columns={columns} rows={characters} rowKey="id" onRowClick={(row) => openDetail(row.id || row.name)} />
            </AsyncState>
          </section>
        </div>
      </AsyncState>

      <Modal open={showCharForm} onClose={() => setShowCharForm(false)} title="添加人物">
        <form className={styles.formBody} onSubmit={handleAddCharacter}>
          <input className={styles.formInput} placeholder="姓名" value={charForm.name}
                 onChange={(e) => setCharForm({ ...charForm, name: e.target.value })} required />
          <select className={styles.formInput} value={charForm.role}
                  onChange={(e) => setCharForm({ ...charForm, role: e.target.value })}>
            <option value="主角">主角</option>
            <option value="配角">配角</option>
            <option value="反派">反派</option>
            <option value="导师">导师</option>
          </select>
          <textarea className={styles.textarea} rows="2" placeholder="性格描述" value={charForm.personality}
                    onChange={(e) => setCharForm({ ...charForm, personality: e.target.value })} />
          <textarea className={styles.textarea} rows="2" placeholder="能力/技能" value={charForm.abilities}
                    onChange={(e) => setCharForm({ ...charForm, abilities: e.target.value })} />
          <textarea className={styles.textarea} rows="2" placeholder="备注" value={charForm.notes}
                    onChange={(e) => setCharForm({ ...charForm, notes: e.target.value })} />
          <Button variant="primary" type="submit" loading={submitting} block>添加</Button>
        </form>
      </Modal>

      <Modal open={!!detailId} onClose={() => setDetailId(null)} title={detailData?.name || '人物详情'}>
        {loadingDetail ? <div className={styles.detailSkeleton} /> : detailData ? (
          <div className={styles.detailBody}>
            {Object.entries(detailData).filter(([k]) => !['id', 'book_id'].includes(k)).map(([k, v]) => v && (
              <div key={k}>
                <h4>{k}</h4>
                <p>{typeof v === 'object' ? JSON.stringify(v, null, 2) : String(v)}</p>
              </div>
            ))}
          </div>
        ) : null}
      </Modal>
    </div>
  );
}

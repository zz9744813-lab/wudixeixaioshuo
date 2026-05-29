import React, { useState, useEffect } from 'react';
import api from '../services/api';
import './BibleEditor.css';

function BibleEditor({ projectId }) {
  const [activeTab, setActiveTab] = useState('world');
  const [bible, setBible] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [worldSetting, setWorldSetting] = useState('');
  const [characters, setCharacters] = useState([]);
  const [outline, setOutline] = useState([]);
  const [newCharacter, setNewCharacter] = useState({
    name: '',
    role: '主角',
    age: '',
    appearance: '',
    personality: '',
    desires: '',
    flaws: '',
    background: '',
    abilities: ''
  });

  useEffect(() => {
    if (projectId) {
      fetchBible();
    }
  }, [projectId]);

  const fetchBible = async () => {
    try {
      const response = await api.get(`/projects/${projectId}/bible`);
      setBible(response.data);
      setWorldSetting(response.data.world_setting || '');
      setCharacters(response.data.characters || []);
      setOutline(response.data.chapter_outline || []);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching bible:', error);
      setLoading(false);
    }
  };

  const handleGenerateWorld = async () => {
    setGenerating(true);
    try {
      const response = await api.post(
        `/projects/${projectId}/bible/world-setting/generate`,
        { hint: '' }
      );
      setWorldSetting(response.data.content);
      setGenerating(false);
    } catch (error) {
      console.error('Error generating world:', error);
      setGenerating(false);
    }
  };

  const handleSaveWorld = async () => {
    try {
      await api.put(`/projects/${projectId}/bible/world-setting`, {
        world_setting: worldSetting
      });
      alert('世界观已保存');
    } catch (error) {
      console.error('Error saving world:', error);
    }
  };

  const handleAddCharacter = async () => {
    try {
      await api.post(`/projects/${projectId}/bible/characters`, newCharacter);
      setNewCharacter({ name: '', role: '主角', age: '', appearance: '', personality: '', desires: '', flaws: '', background: '', abilities: '' });
      fetchBible();
    } catch (error) {
      console.error('Error adding character:', error);
    }
  };

  const handleGenerateCharacter = async (role) => {
    setGenerating(true);
    try {
      await api.post(`/projects/${projectId}/bible/characters/generate?role=${role}`);
      fetchBible();
      setGenerating(false);
    } catch (error) {
      console.error('Error generating character:', error);
      setGenerating(false);
    }
  };

  const handleGenerateOutline = async () => {
    setGenerating(true);
    try {
      await api.post(`/projects/${projectId}/bible/outline/generate`, {
        volume_count: 3, chapters_per_volume: 30
      });
      fetchBible();
      setGenerating(false);
    } catch (error) {
      console.error('Error generating outline:', error);
      setGenerating(false);
    }
  };

  if (loading) return <div className="loading">加载中...</div>;

  return (
    <div className="bible-editor">
      <div className="bible-tabs">
        <button className={activeTab === 'world' ? 'active' : ''} onClick={() => setActiveTab('world')}>世界观</button>
        <button className={activeTab === 'characters' ? 'active' : ''} onClick={() => setActiveTab('characters')}>人物</button>
        <button className={activeTab === 'outline' ? 'active' : ''} onClick={() => setActiveTab('outline')}>大纲</button>
      </div>

      {activeTab === 'world' && (
        <div className="bible-section">
          <div className="section-header">
            <h3>世界观设定</h3>
            <div className="section-actions">
              <button className="btn-secondary" onClick={handleGenerateWorld} disabled={generating}>
                {generating ? '生成中...' : 'AI生成'}
              </button>
              <button className="btn-primary" onClick={handleSaveWorld}>保存</button>
            </div>
          </div>
          <textarea
            className="world-textarea"
            value={worldSetting}
            onChange={(e) => setWorldSetting(e.target.value)}
            placeholder="在这里输入世界观设定..."
            rows={20}
          />
        </div>
      )}

      {activeTab === 'characters' && (
        <div className="bible-section">
          <div className="section-header">
            <h3>人物卡</h3>
            <div className="section-actions">
              <button className="btn-secondary" onClick={() => handleGenerateCharacter('主角')} disabled={generating}>生成主角</button>
              <button className="btn-secondary" onClick={() => handleGenerateCharacter('反派')} disabled={generating}>生成反派</button>
            </div>
          </div>

          <div className="character-list">
            {characters.map((char, idx) => (
              <div key={idx} className="character-card">
                <div className="character-header">
                  <h4>{char.name || char.role}</h4>
                  <span className="role-badge">{char.role}</span>
                </div>
                <p className="character-summary">{char.appearance?.substring(0, 100)}...</p>
              </div>
            ))}
          </div>

          <div className="add-character-form">
            <h4>添加人物</h4>
            <div className="form-row">
              <input placeholder="姓名" value={newCharacter.name} onChange={(e) => setNewCharacter({...newCharacter, name: e.target.value})} />
              <select value={newCharacter.role} onChange={(e) => setNewCharacter({...newCharacter, role: e.target.value})}>
                <option value="主角">主角</option>
                <option value="配角">配角</option>
                <option value="反派">反派</option>
                <option value="导师">导师</option>
              </select>
            </div>
            <textarea placeholder="外貌" value={newCharacter.appearance} onChange={(e) => setNewCharacter({...newCharacter, appearance: e.target.value})} />
            <textarea placeholder="性格" value={newCharacter.personality} onChange={(e) => setNewCharacter({...newCharacter, personality: e.target.value})} />
            <button className="btn-primary" onClick={handleAddCharacter}>添加</button>
          </div>
        </div>
      )}

      {activeTab === 'outline' && (
        <div className="bible-section">
          <div className="section-header">
            <h3>章节大纲</h3>
            <button className="btn-secondary" onClick={handleGenerateOutline} disabled={generating}>
              {generating ? '生成中...' : '生成大纲'}
            </button>
          </div>
          <div className="outline-list">
            {outline.slice(0, 20).map((chapter) => (
              <div key={chapter.chapter_index} className="outline-item">
                <span className="chapter-index">第{chapter.chapter_index}章</span>
                <span className="chapter-title">{chapter.title}</span>
              </div>
            ))}
            {outline.length > 20 && <p className="more-chapters">...还有 {outline.length - 20} 章</p>}
          </div>
        </div>
      )}
    </div>
  );
}

export default BibleEditor;

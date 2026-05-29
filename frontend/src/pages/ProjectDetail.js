import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import api from '../services/api';
import BibleEditor from './BibleEditor';
import './ProjectDetail.css';

function ProjectDetail() {
  const { id } = useParams();
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    fetchProject();
  }, [id]);

  const fetchProject = async () => {
    try {
      const response = await api.get(`/projects/${id}`);
      const data = await response.json();
      setProject(data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching project:', error);
      setLoading(false);
    }
  };

  const handleStart = async () => {
    try {
      await api.post(`/projects/${id}/start`);
      fetchProject();
    } catch (error) {
      console.error('Error starting project:', error);
    }
  };

  const handlePause = async () => {
    try {
      await api.post(`/projects/${id}/pause`);
      fetchProject();
    } catch (error) {
      console.error('Error pausing project:', error);
    }
  };

  if (loading) {
    return <div className="loading">加载中...</div>;
  }

  if (!project) {
    return <div className="error">项目不存在</div>;
  }

  return (
    <div className="project-detail">
      <header className="page-header">
        <div className="header-content">
          <h1>{project.name}</h1>
          <div className="header-actions">
            {project.status === 'active' ? (
              <button className="btn-warning" onClick={handlePause}>
                ⏸️ 暂停
              </button>
            ) : (
              <button className="btn-primary" onClick={handleStart}>
                ▶️ 启动
              </button>
            )}
          </div>
        </div>
        <p className="project-description">{project.description || '暂无描述'}</p>
      </header>

      <div className="project-tabs">
        <button
          className={activeTab === 'overview' ? 'active' : ''}
          onClick={() => setActiveTab('overview')}
        >
          概览
        </button>
        <button
          className={activeTab === 'bible' ? 'active' : ''}
          onClick={() => setActiveTab('bible')}
        >
          小说圣经
        </button>
        <button
          className={activeTab === 'chapters' ? 'active' : ''}
          onClick={() => setActiveTab('chapters')}
        >
          章节
        </button>
        <button
          className={activeTab === 'settings' ? 'active' : ''}
          onClick={() => setActiveTab('settings')}
        >
          设置
        </button>
      </div>

      <div className="project-content">
        {activeTab === 'overview' && (
          <div className="overview-tab">
            <div className="stats-row">
              <div className="stat-box">
                <span className="stat-label">状态</span>
                <span className="stat-value status">{project.status}</span>
              </div>
              <div className="stat-box">
                <span className="stat-label">题材</span>
                <span className="stat-value">{project.genre}</span>
              </div>
              <div className="stat-box">
                <span className="stat-label">目标读者</span>
                <span className="stat-value">{project.target_reader || '未设置'}</span>
              </div>
              <div className="stat-box">
                <span className="stat-label">当前章节</span>
                <span className="stat-value">{project.progress.current_chapter}</span>
              </div>
              <div className="stat-box">
                <span className="stat-label">已写字数</span>
                <span className="stat-value">{project.progress.total_words.toLocaleString()}</span>
              </div>
            </div>

            <div className="goals-section">
              <h3>目标设置</h3>
              <div className="goals-grid">
                <div className="goal-item">
                  <label>总字数目标</label>
                  <span>{project.goals.total_word.toLocaleString()}</span>
                </div>
                <div className="goal-item">
                  <label>每日字数</label>
                  <span>{project.goals.daily_word.toLocaleString()}</span>
                </div>
                <div className="goal-item">
                  <label>每章字数</label>
                  <span>{project.goals.chapter_word.toLocaleString()}</span>
                </div>
              </div>
            </div>

            <div className="quality-section">
              <h3>质量目标</h3>
              <div className="quality-bars">
                <div className="quality-item">
                  <label>剧情推进</label>
                  <div className="progress-bar">
                    <div className="progress" style={{ width: `${project.quality.plot_progress * 10}%` }}></div>
                  </div>
                  <span>{project.quality.plot_progress}/10</span>
                </div>
                <div className="quality-item">
                  <label>爽点密度</label>
                  <div className="progress-bar">
                    <div className="progress" style={{ width: `${project.quality.satisfaction * 10}%` }}></div>
                  </div>
                  <span>{project.quality.satisfaction}/10</span>
                </div>
                <div className="quality-item">
                  <label>质量阈值</label>
                  <div className="progress-bar">
                    <div className="progress" style={{ width: `${project.quality.threshold}%` }}></div>
                  </div>
                  <span>{project.quality.threshold}/100</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'bible' && (
          <div className="bible-tab">
            <BibleEditor projectId={project.id} />
          </div>
        )}

        {activeTab === 'chapters' && (
          <div className="chapters-tab">
            <h3>章节列表</h3>
            <p className="empty">暂无章节</p>
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="settings-tab">
            <h3>项目设置</h3>
            <p>设置功能开发中...</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default ProjectDetail;

import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import './Projects.css';

function Projects() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [newProject, setNewProject] = useState({
    name: '',
    description: '',
    genre: '',
    daily_word_goal: 3000,
  });

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      const response = await api.get("/projects/");
      const data = await response.json();
      setProjects(data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching projects:', error);
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      const response = await api.post("/projects/", newProject);
      if (response.data) {
        setShowForm(false);
        setNewProject({ name: '', description: '', genre: '', daily_word_goal: 3000 });
        fetchProjects();
      }
    } catch (error) {
      console.error('Error creating project:', error);
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      draft: '#888',
      active: '#10b981',
      paused: '#f59e0b',
      completed: '#3b82f6',
      archived: '#6b7280',
    };
    return colors[status] || '#888';
  };

  const getStatusLabel = (status) => {
    const labels = {
      draft: '草稿',
      active: '进行中',
      paused: '暂停',
      completed: '已完成',
      archived: '已归档',
    };
    return labels[status] || status;
  };

  if (loading) {
    return <div className="loading">加载中...</div>;
  }

  return (
    <div className="projects-page">
      <header className="page-header">
        <h1>📖 小说项目</h1>
        <button className="btn-primary" onClick={() => setShowForm(true)}>
          ➕ 新建项目
        </button>
      </header>

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>新建项目</h2>
            <form onSubmit={handleCreate}>
              <div className="form-group">
                <label>项目名称</label>
                <input
                  type="text"
                  value={newProject.name}
                  onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>题材</label>
                <input
                  type="text"
                  value={newProject.genre}
                  onChange={(e) => setNewProject({ ...newProject, genre: e.target.value })}
                  placeholder="如：玄幻、都市、言情..."
                />
              </div>
              <div className="form-group">
                <label>描述</label>
                <textarea
                  value={newProject.description}
                  onChange={(e) => setNewProject({ ...newProject, description: e.target.value })}
                  rows={3}
                />
              </div>
              <div className="form-group">
                <label>每日目标字数</label>
                <input
                  type="number"
                  value={newProject.daily_word_goal}
                  onChange={(e) => setNewProject({ ...newProject, daily_word_goal: parseInt(e.target.value) })}
                />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowForm(false)}>
                  取消
                </button>
                <button type="submit" className="btn-primary">
                  创建
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="projects-grid">
        {projects.length === 0 ? (
          <div className="empty-state">
            <p>暂无项目</p>
            <button className="btn-primary" onClick={() => setShowForm(true)}>
              创建第一个项目
            </button>
          </div>
        ) : (
          projects.map((project) => (
            <Link to={`/projects/${project.id}`} key={project.id} className="project-card">
              <div className="project-header">
                <h3>{project.name}</h3>
                <span
                  className="status-badge"
                  style={{ background: getStatusColor(project.status) }}
                >
                  {getStatusLabel(project.status)}
                </span>
              </div>
              <p className="project-genre">{project.genre || '未分类'}</p>
              <div className="project-stats">
                <div className="stat">
                  <span className="stat-label">当前章节</span>
                  <span className="stat-value">{project.current_chapter_index}</span>
                </div>
                <div className="stat">
                  <span className="stat-label">已写字数</span>
                  <span className="stat-value">{project.total_words_written.toLocaleString()}</span>
                </div>
              </div>
              <p className="project-date">
                创建于 {new Date(project.created_at).toLocaleDateString()}
              </p>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}

export default Projects;

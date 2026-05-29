import React, { useState, useEffect } from 'react';
import api from '../services/api';
import './Techniques.css';

function Techniques() {
  const [techniques, setTechniques] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState('all');

  useEffect(() => {
    fetchTechniques();
  }, []);

  const fetchTechniques = async () => {
    try {
      const response = await api.get("/techniques/");
      const data = await response.json();
      setTechniques(data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching techniques:', error);
      setLoading(false);
    }
  };

  const categories = [
    { id: 'all', label: '全部' },
    { id: 'structure', label: '结构' },
    { id: 'character', label: '人物' },
    { id: 'pacing', label: '节奏' },
    { id: 'hook', label: '钩子' },
    { id: 'emotion', label: '情绪' },
    { id: 'style', label: '文风' },
  ];

  const filteredTechniques = selectedCategory === 'all'
    ? techniques
    : techniques.filter(t => t.category === selectedCategory);

  if (loading) {
    return <div className="loading">加载中...</div>;
  }

  return (
    <div className="techniques-page">
      <header className="page-header">
        <h1>🎯 技巧库</h1>
        <p>从拆书中提取的写作技巧</p>
      </header>

      <div className="category-filter">
        {categories.map(cat => (
          <button
            key={cat.id}
            className={selectedCategory === cat.id ? 'active' : ''}
            onClick={() => setSelectedCategory(cat.id)}
          >
            {cat.label}
          </button>
        ))}
      </div>

      <div className="techniques-grid">
        {filteredTechniques.length === 0 ? (
          <div className="empty-state">
            <p>暂无技巧卡</p>
            <p className="hint">先拆书分析，这里会显示提取的写作技巧</p>
          </div>
        ) : (
          filteredTechniques.map((tech) => (
            <div key={tech.id} className="technique-card">
              <div className="technique-header">
                <span className="category-badge">{tech.category}</span>
                <span className="confidence">置信度: {(tech.confidence_score * 100).toFixed(0)}%</span>
              </div>
              <h3>{tech.title}</h3>
              <p className="description">{tech.description}</p>
              <div className="technique-footer">
                <span>使用 {tech.usage_count} 次</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default Techniques;

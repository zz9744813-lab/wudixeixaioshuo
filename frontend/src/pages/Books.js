import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { API_BASE_URL } from '../services/api';
import './Books.css';

function Books() {
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    fetchBooks();
  }, []);

  const fetchBooks = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/books/`);
      const data = await response.json();
      setBooks(data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching books:', error);
      setLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE_URL}/books/upload`, {
        method: 'POST',
        body: formData,
      });
      if (response.ok) {
        fetchBooks();
      }
    } catch (error) {
      console.error('Error uploading book:', error);
    }
    setUploading(false);
  };

  const getStatusColor = (status) => {
    const colors = {
      imported: '#3b82f6',
      processing: '#f59e0b',
      splitting: '#8b5cf6',
      analyzing: '#ec4899',
      completed: '#10b981',
      failed: '#ef4444',
    };
    return colors[status] || '#888';
  };

  const getStatusLabel = (status) => {
    const labels = {
      imported: '已导入',
      processing: '处理中',
      splitting: '分章中',
      analyzing: '分析中',
      completed: '已完成',
      failed: '失败',
    };
    return labels[status] || status;
  };

  if (loading) {
    return <div className="loading">加载中...</div>;
  }

  return (
    <div className="books-page">
      <header className="page-header">
        <h1>📚 拆书学习</h1>
        <div className="upload-area">
          <input
            type="file"
            id="book-upload"
            accept=".txt,.md,.epub,.docx,.pdf"
            onChange={handleFileUpload}
            style={{ display: 'none' }}
          />
          <label htmlFor="book-upload" className="btn-primary">
            {uploading ? '⏳ 上传中...' : '📤 上传书籍'}
          </label>
        </div>
      </header>

      <div className="books-grid">
        {books.length === 0 ? (
          <div className="empty-state">
            <p>暂无书籍</p>
            <p className="hint">上传小说文件开始学习拆解</p>
          </div>
        ) : (
          books.map((book) => (
            <Link to={`/books/${book.id}`} key={book.id} className="book-card">
              <div className="book-header">
                <h3>{book.title}</h3>
                <span
                  className="status-badge"
                  style={{ background: getStatusColor(book.status) }}
                >
                  {getStatusLabel(book.status)}
                </span>
              </div>
              <p className="book-author">{book.author_alias || '未知作者'}</p>
              <p className="book-genre">{book.genre || '未分类'}</p>
              <div className="book-stats">
                <span>📄 {book.total_chapters} 章</span>
                <span>📝 {(book.total_words || 0).toLocaleString()} 字</span>
              </div>
              <p className="book-date">
                导入于 {new Date(book.created_at).toLocaleDateString()}
              </p>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}

export default Books;

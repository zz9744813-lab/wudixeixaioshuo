import React from 'react';
import { useParams } from 'react-router-dom';

function BookDetail() {
  const { id } = useParams();

  return (
    <div className="book-detail">
      <header className="page-header">
        <h1>📚 书籍详情</h1>
      </header>
      <div className="content">
        <p>书籍 ID: {id}</p>
        <p>功能开发中...</p>
      </div>
    </div>
  );
}

export default BookDetail;

/**
 * App - 主应用组件
 */
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { SSEProvider } from './hooks/SSEContext';
import { WorkerMonitor } from './components/WorkerMonitor';
import './App.css';

function Dashboard() {
  return (
    <div className="dashboard">
      <h1>24小时小说 Agent 工作台</h1>
      <div className="dashboard-content">
        <WorkerMonitor />
      </div>
    </div>
  );
}

function App() {
  return (
    <SSEProvider>
      <Router>
        <div className="app">
          <nav className="navbar">
            <div className="nav-brand">小说 Agent</div>
            <ul className="nav-links">
              <li><Link to="/">Dashboard</Link></li>
              <li><Link to="/projects">Projects</Link></li>
              <li><Link to="/tasks">Tasks</Link></li>
              <li><Link to="/models">Models</Link></li>
            </ul>
          </nav>

          <main className="main-content">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/projects" element={<div>Projects Page</div>} />
              <Route path="/tasks" element={<div>Tasks Page</div>} />
              <Route path="/models" element={<div>Models Page</div>} />
            </Routes>
          </main>
        </div>
      </Router>
    </SSEProvider>
  );
}

export default App;

import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Projects from './pages/Projects';
import ProjectDetail from './pages/ProjectDetail';
import Books from './pages/Books';
import BookDetail from './pages/BookDetail';
import Techniques from './pages/Techniques';
import WritingFactory from './pages/WritingFactory';
import AgentConsole from './pages/AgentConsole';
import Tasks from './pages/Tasks';
import ModelConfig from './pages/ModelConfig';
import Feedback from './pages/Feedback';
import Evolution from './pages/Evolution';
import Logs from './pages/Logs';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/projects/:id" element={<ProjectDetail />} />
          <Route path="/books" element={<Books />} />
          <Route path="/books/:id" element={<BookDetail />} />
          <Route path="/techniques" element={<Techniques />} />
          <Route path="/factory" element={<WritingFactory />} />
          <Route path="/agents" element={<AgentConsole />} />
          <Route path="/tasks" element={<Tasks />} />
          <Route path="/models" element={<ModelConfig />} />
          <Route path="/feedback" element={<Feedback />} />
          <Route path="/evolution" element={<Evolution />} />
          <Route path="/logs" element={<Logs />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;

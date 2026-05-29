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
import FeedbackCenter from './pages/FeedbackCenter';
import EvolutionCenter from './pages/EvolutionCenter';
import ExportPage from './pages/ExportPage';
import Logs from './pages/Logs';
import WorkerDashboard from './pages/WorkerDashboard';
import UsageDashboard from './pages/UsageDashboard';
import PromptTemplates from './pages/PromptTemplates';

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
          <Route path="/feedback" element={<FeedbackCenter />} />
          <Route path="/evolution" element={<EvolutionCenter />} />
          <Route path="/worker" element={<WorkerDashboard />} />
          <Route path="/export" element={<ExportPage />} />
          <Route path="/logs" element={<Logs />} />
          <Route path="/usage" element={<UsageDashboard />} />
          <Route path="/prompts" element={<PromptTemplates />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;

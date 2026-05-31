import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import { ToastProvider } from './contexts/ToastContext';
import Dashboard from './pages/Dashboard';
import Projects from './pages/Projects';
import ProjectDetail from './pages/ProjectDetail';
import Books from './pages/Books';
import BookDetail from './pages/BookDetail';
import Techniques from './pages/Techniques';
import WritingFactory from './pages/WritingFactory';
import AgentConsole from './pages/AgentConsole';
import Tasks from './pages/Tasks';
import TaskDetail from './pages/TaskDetail';
import ModelConfig from './pages/ModelConfig';
import FeedbackCenter from './pages/FeedbackCenter';
import EvolutionCenter from './pages/EvolutionCenter';
import ExportPage from './pages/ExportPage';
import Logs from './pages/Logs';
import WorkerDashboard from './pages/WorkerDashboard';
import UsageDashboard from './pages/UsageDashboard';
import PromptTemplates from './pages/PromptTemplates';
import AgentOrchestratorPage from './pages/AgentOrchestratorPage';
import AgentRunDetailPage from './pages/AgentRunDetailPage';
import LLMRouterPage from './pages/LLMRouterPage';
import ResearchAgentPage from './pages/ResearchAgentPage';
import EvolutionAutoPage from './pages/EvolutionAutoPage';
import ReaderTrainingPage from './pages/ReaderTrainingPage';
import ToastContainer from './pages/ToastContainer';

function App() {
  return (
    <ToastProvider><Router>
      <Layout>
      <ToastContainer />
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
          <Route path="/tasks/:id" element={<TaskDetail />} />
          <Route path="/models" element={<ModelConfig />} />
          <Route path="/feedback" element={<FeedbackCenter />} />
          <Route path="/evolution" element={<EvolutionCenter />} />
          <Route path="/worker" element={<WorkerDashboard />} />
          <Route path="/export" element={<ExportPage />} />
          <Route path="/logs" element={<Logs />} />
          <Route path="/usage" element={<UsageDashboard />} />
          <Route path="/prompts" element={<PromptTemplates />} />
          <Route path="/agent-orchestrator" element={<AgentOrchestratorPage />} />
          <Route path="/agent-runs/:id" element={<AgentRunDetailPage />} />
          <Route path="/llm-routes" element={<LLMRouterPage />} />
          <Route path="/research-agent" element={<ResearchAgentPage />} />
          <Route path="/evolution-auto" element={<EvolutionAutoPage />} />
          <Route path="/reader-training" element={<ReaderTrainingPage />} />
</Routes>
      </Layout>
    </Router></ToastProvider>
  );
}

export default App;

import React from 'react'
import { Routes, Route } from 'react-router-dom'
import MainLayout from './components/layout/MainLayout'
import HomePage from './pages/HomePage'
import WritingPage from './pages/WritingPage'
import OutlinePage from './pages/OutlinePage'
import LiteraturePage from './pages/LiteraturePage'
import SettingsPage from './pages/SettingsPage'
import AIAssistantPage from './pages/AIAssistantPage'
import ReportsPage from './pages/ReportsPage'
import FeaturesPage from './pages/FeaturesPage'
import KnowledgeGraphPage from './pages/KnowledgeGraphPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<MainLayout />}>
        <Route index element={<HomePage />} />
        <Route path="writing" element={<WritingPage />} />
        <Route path="outline" element={<OutlinePage />} />
        <Route path="literature" element={<LiteraturePage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="ai-assistant" element={<AIAssistantPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="features" element={<FeaturesPage />} />
        <Route path="knowledge-graph" element={<KnowledgeGraphPage />} />
      </Route>
    </Routes>
  )
}

export default App

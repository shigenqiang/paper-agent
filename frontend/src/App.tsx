import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import ResearchPage from './pages/ResearchPage'
import PapersPage from './pages/PapersPage'
import ReportPage from './pages/ReportPage'
import GraphPage from './pages/GraphPage'
import ChatPage from './pages/ChatPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<ResearchPage />} />
        <Route path="papers" element={<PapersPage />} />
        <Route path="reports" element={<ReportPage />} />
        <Route path="graph" element={<GraphPage />} />
        <Route path="chat" element={<ChatPage />} />
      </Route>
    </Routes>
  )
}

import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout/Layout'
import LibraryPage from './pages/LibraryPage'
import GraphPage from './pages/GraphPage'
import QAPage from './pages/QAPage'
import ReportsPage from './pages/ReportsPage'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/library" replace />} />
        <Route path="/library" element={<LibraryPage />} />
        <Route path="/graph" element={<GraphPage />} />
        <Route path="/qa" element={<QAPage />} />
        <Route path="/reports" element={<ReportsPage />} />
      </Route>
    </Routes>
  )
}

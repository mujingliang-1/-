import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import AppLayout from './components/AppLayout'
import { InspectPage } from './pages/Inspect'
import { HistoryPage } from './pages/History'
import { StandardsPage } from './pages/Standards'
import './styles.css'

function App() {
  return (
    <BrowserRouter>
      <AppLayout>
        <Routes>
          <Route path="/" element={<Navigate to="/inspect" replace />} />
          <Route path="/inspect" element={<InspectPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/history/:id" element={<HistoryPage />} />
          <Route path="/standards" element={<StandardsPage />} />
        </Routes>
      </AppLayout>
    </BrowserRouter>
  )
}

createRoot(document.getElementById('root')!).render(<App />)

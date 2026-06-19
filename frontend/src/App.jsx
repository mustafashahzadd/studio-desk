import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import JobDetail from './pages/JobDetail'
import Approval from './pages/Approval'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"                    element={<Dashboard />} />
        <Route path="/jobs/:jobId"         element={<JobDetail />} />
        <Route path="/jobs/:jobId/approve" element={<Approval />} />
      </Routes>
    </BrowserRouter>
  )
}

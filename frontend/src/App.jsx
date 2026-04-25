import { Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar'
import ProfilesPage from './pages/ProfilesPage'
import SetupPage from './pages/SetupPage'
import DashboardPage from './pages/DashboardPage'

export default function App() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar />
      <main style={{ flex: 1 }}>
        <Routes>
          <Route path="/" element={<Navigate to="/profiles" replace />} />
          <Route path="/profiles" element={<ProfilesPage />} />
          <Route path="/profiles/:name/setup" element={<SetupPage />} />
          <Route path="/profiles/:name/dashboard" element={<DashboardPage />} />
        </Routes>
      </main>
    </div>
  )
}

import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, NavLink, useNavigate } from 'react-router-dom'
import './App.css'
import HomePage from './pages/HomePage'
import ComplaintPage from './pages/ComplaintPage'
import { healthCheck } from './services/api'

function Navbar() {
  const navigate = useNavigate()
  const [apiOnline, setApiOnline] = useState(null)

  useEffect(() => {
    healthCheck()
      .then(() => setApiOnline(true))
      .catch(() => setApiOnline(false))
  }, [])

  return (
    <nav className="navbar">
      <a className="navbar-brand" href="/" onClick={e => { e.preventDefault(); navigate('/') }}>
        <div className="navbar-logo">EQ</div>
        <div>
          <span className="navbar-name">EmergencyQ</span>
          <span className="navbar-tagline">AI Triage System</span>
        </div>
      </a>

      <div className="navbar-links">
        <NavLink to="/" end className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
          Home
        </NavLink>
        <NavLink to="/complaint" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
          File Complaint
        </NavLink>

        {apiOnline !== null && (
          <div className={`status-dot${apiOnline ? '' : ' offline'}`}>
            {apiOnline ? 'API Online' : 'API Offline'}
          </div>
        )}

        <NavLink to="/complaint" className="nav-cta">
          Report Now →
        </NavLink>
      </div>
    </nav>
  )
}

function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <Navbar />
        <main className="page-content">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/complaint" element={<ComplaintPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App

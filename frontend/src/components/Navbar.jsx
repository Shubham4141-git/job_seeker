import { Link, useLocation } from 'react-router-dom'

export default function Navbar() {
  const loc = useLocation()
  return (
    <nav style={{
      background: 'var(--surface)',
      borderBottom: '1px solid var(--border)',
      padding: '0 24px',
      height: 56,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
    }}>
      <Link to="/profiles" style={{ fontWeight: 700, fontSize: 18, color: 'var(--primary)' }}>
        Job Seeker
      </Link>
      <div style={{ display: 'flex', gap: 20, color: 'var(--text-muted)', fontSize: 14 }}>
        <Link to="/profiles" style={{ color: loc.pathname === '/profiles' ? 'var(--text)' : 'var(--text-muted)' }}>
          Profiles
        </Link>
      </div>
    </nav>
  )
}

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'

export default function ProfilesPage() {
  const [profiles, setProfiles] = useState([])
  const [loading, setLoading] = useState(true)
  const [newName, setNewName] = useState('')
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')
  const [configStatus, setConfigStatus] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    load()
    api.configStatus().then(setConfigStatus).catch(() => {})
  }, [])

  async function load() {
    setLoading(true)
    try {
      const data = await api.getProfiles()
      setProfiles(data.profiles)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleCreate(e) {
    e.preventDefault()
    if (!newName.trim()) return
    setCreating(true)
    setError('')
    try {
      await api.createProfile(newName.trim())
      setNewName('')
      await load()
    } catch (e) {
      setError(e.message)
    } finally {
      setCreating(false)
    }
  }

  async function handleDelete(name) {
    if (!confirm(`Delete profile "${name}"? This cannot be undone.`)) return
    try {
      await api.deleteProfile(name)
      await load()
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div className="page">
      <div className="flex justify-between items-center mb-2">
        <h1 className="page-title" style={{ margin: 0 }}>Profiles</h1>
      </div>

      {configStatus && (
        <div className="alert alert-info" style={{ marginBottom: 20, fontSize: 12 }}>
          API Keys — Adzuna: {configStatus.adzuna ? '✅' : '❌'}  ·
          OpenAI: {configStatus.openai ? '✅' : '❌'}  ·
          Gmail: {configStatus.gmail ? '✅' : '❌'}
        </div>
      )}

      {error && <div className="alert alert-error">{error}</div>}

      <form onSubmit={handleCreate} className="card flex gap-3 items-center" style={{ marginBottom: 24 }}>
        <input
          placeholder="New profile name (e.g. shubham_ml)"
          value={newName}
          onChange={e => setNewName(e.target.value)}
          style={{ flex: 1 }}
          disabled={creating}
        />
        <button type="submit" className="btn-primary" disabled={creating || !newName.trim()}>
          {creating ? <span className="spinner" /> : 'Create Profile'}
        </button>
      </form>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 40 }}><span className="spinner" /></div>
      ) : profiles.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 48, color: 'var(--text-muted)' }}>
          No profiles yet. Create one above to get started.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {profiles.map(p => (
            <div key={p.name} className="card flex justify-between items-center">
              <div>
                <div style={{ fontWeight: 600, fontSize: 16 }}>{p.name}</div>
                <div style={{ marginTop: 6, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  <span className={`badge ${p.has_resume ? 'badge-success' : 'badge-warning'}`}>
                    {p.has_resume ? '✓ Resume' : '✗ No resume'}
                  </span>
                  <span className={`badge ${p.has_prefs ? 'badge-success' : 'badge-warning'}`}>
                    {p.has_prefs ? '✓ Preferences' : '✗ No preferences'}
                  </span>
                  <span className={`badge ${p.has_email ? 'badge-success' : 'badge-warning'}`}>
                    {p.has_email ? '✓ Email set' : '✗ No email'}
                  </span>
                </div>
                {p.recipient_email && (
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>→ {p.recipient_email}</div>
                )}
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="btn-secondary" onClick={() => navigate(`/profiles/${p.name}/setup`)}>
                  {p.has_resume && p.has_prefs ? 'Re-setup' : 'Setup'}
                </button>
                {p.has_resume && p.has_prefs && (
                  <button className="btn-primary" onClick={() => navigate(`/profiles/${p.name}/dashboard`)}>
                    Dashboard
                  </button>
                )}
                <button className="btn-danger" onClick={() => handleDelete(p.name)}>Delete</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

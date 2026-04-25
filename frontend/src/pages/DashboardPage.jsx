import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api'
import JobCard from '../components/JobCard'

export default function DashboardPage() {
  const { name } = useParams()
  const navigate = useNavigate()
  const [profile, setProfile] = useState(null)
  const [jobs, setJobs] = useState([])
  const [selected, setSelected] = useState(new Set())
  const [fetching, setFetching] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [msg, setMsg] = useState('')
  const [totalFetched, setTotalFetched] = useState(null)

  useEffect(() => {
    api.getProfile(name).then(setProfile).catch(() => {})
  }, [name])

  async function handleFetch() {
    setFetching(true)
    setError('')
    setMsg('')
    setJobs([])
    setSelected(new Set())
    try {
      const data = await api.fetchJobs(name)
      setJobs(data.jobs || [])
      setTotalFetched(data.total_fetched)
      if ((data.jobs || []).length === 0) {
        setMsg('No new matching jobs found. All recent jobs may already have been sent.')
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setFetching(false)
    }
  }

  function toggleJob(job) {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(job.id) ? next.delete(job.id) : next.add(job.id)
      return next
    })
  }

  function toggleAll() {
    if (selected.size === jobs.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(jobs.map(j => j.id)))
    }
  }

  async function handleSend() {
    const toSend = jobs.filter(j => selected.has(j.id))
    if (toSend.length === 0) { setError('Select at least one job to send'); return }
    setSending(true)
    setError('')
    setMsg('')
    try {
      const data = await api.sendEmail(name, toSend)
      if (data.ok) {
        setMsg(data.message)
        setSelected(new Set())
      } else {
        setError(data.message)
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setSending(false)
    }
  }

const prefs = profile?.preferences || {}
  const recipientEmail = profile?.recipient_email || ''

  return (
    <div className="page">
      <div style={{ marginBottom: 8, color: 'var(--text-muted)', fontSize: 13 }}>
        <span onClick={() => navigate('/profiles')} style={{ cursor: 'pointer' }}>← Profiles</span>
        <span style={{ margin: '0 6px' }}>/</span>
        <span>{name}</span>
      </div>

      <div className="flex justify-between items-center" style={{ marginBottom: 24 }}>
        <h1 className="page-title" style={{ margin: 0 }}>Dashboard — {name}</h1>
        <button className="btn-secondary" onClick={() => navigate(`/profiles/${name}/setup`)}>
          Re-setup
        </button>
      </div>

      {/* Profile summary */}
      {profile?.profile && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="flex gap-4" style={{ flexWrap: 'wrap' }}>
            <div>
              <div style={{ color: 'var(--text-muted)', fontSize: 11, marginBottom: 2 }}>NAME</div>
              <div style={{ fontWeight: 600 }}>{profile.profile.full_name || name}</div>
            </div>
            <div>
              <div style={{ color: 'var(--text-muted)', fontSize: 11, marginBottom: 2 }}>ROLE</div>
              <div>{profile.profile.current_job_title || '—'}</div>
            </div>
            <div>
              <div style={{ color: 'var(--text-muted)', fontSize: 11, marginBottom: 2 }}>EXPERIENCE</div>
              <div>{profile.profile.total_years_experience ?? '—'} yrs</div>
            </div>
            <div>
              <div style={{ color: 'var(--text-muted)', fontSize: 11, marginBottom: 2 }}>EMAIL TO</div>
              <div style={{ color: 'var(--primary)' }}>{recipientEmail || '—'}</div>
            </div>
          </div>
          {prefs.preferred_job_titles?.length > 0 && (
            <div style={{ marginTop: 10 }}>
              {prefs.preferred_job_titles.map((t, i) => <span key={i} className="tag">{t}</span>)}
              {prefs.preferred_locations?.map((l, i) => <span key={i} className="tag" style={{ color: 'var(--primary)' }}>{l}</span>)}
            </div>
          )}
        </div>
      )}

      {error && <div className="alert alert-error">{error}</div>}
      {msg && <div className="alert alert-success">{msg}</div>}

      {/* Actions */}
      <div className="flex gap-3" style={{ marginBottom: 20, flexWrap: 'wrap' }}>
        <button className="btn-primary" onClick={handleFetch} disabled={fetching}>
          {fetching ? <><span className="spinner" style={{ marginRight: 8 }} />Fetching jobs...</> : '🔍 Fetch & Match Jobs'}
        </button>
        {jobs.length > 0 && (
          <>
            <button className="btn-secondary" onClick={toggleAll}>
              {selected.size === jobs.length ? 'Deselect All' : 'Select All'}
            </button>
            <button className="btn-success" onClick={handleSend} disabled={sending || selected.size === 0}>
              {sending ? <><span className="spinner" style={{ marginRight: 8 }} />Sending...</> : `📧 Send ${selected.size > 0 ? `(${selected.size})` : ''} to Email`}
            </button>
          </>
        )}
      </div>

      {/* Stats */}
      {totalFetched !== null && (
        <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 12 }}>
          Fetched {totalFetched} jobs · {jobs.length} matched after scoring
        </div>
      )}

      {/* Jobs list */}
      {jobs.length > 0 ? (
        <div>
          {jobs.map(job => (
            <JobCard
              key={job.id}
              job={job}
              selected={selected.has(job.id)}
              onToggle={toggleJob}
            />
          ))}
        </div>
      ) : !fetching && totalFetched === null && (
        <div className="card" style={{ textAlign: 'center', padding: 48, color: 'var(--text-muted)' }}>
          Click "Fetch & Match Jobs" to find jobs matching your profile.
        </div>
      )}
    </div>
  )
}

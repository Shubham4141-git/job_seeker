import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api'
import StepIndicator from '../components/StepIndicator'

const STEPS = ['Upload Resume', 'Verify Details', 'Preferences']

function TagInput({ value, onChange, placeholder }) {
  const [input, setInput] = useState('')

  function add(e) {
    if ((e.key === 'Enter' || e.key === ',') && input.trim()) {
      e.preventDefault()
      if (!value.includes(input.trim())) onChange([...value, input.trim()])
      setInput('')
    }
  }

  return (
    <div style={{ border: '1px solid var(--border)', borderRadius: 8, padding: '6px 10px', background: 'var(--surface2)' }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: value.length ? 6 : 0 }}>
        {value.map((t, i) => (
          <span key={i} className="tag" style={{ cursor: 'pointer' }} onClick={() => onChange(value.filter((_, j) => j !== i))}>
            {t} ×
          </span>
        ))}
      </div>
      <input
        value={input}
        onChange={e => setInput(e.target.value)}
        onKeyDown={add}
        placeholder={placeholder}
        style={{ border: 'none', background: 'transparent', padding: 0, outline: 'none', width: '100%' }}
      />
    </div>
  )
}

export default function SetupPage() {
  const { name } = useParams()
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  // Step 0: upload
  const [file, setFile] = useState(null)

  // Step 1: verify extracted profile
  const [profile, setProfile] = useState(null)

  // Step 2: preferences
  const [jobTitles, setJobTitles] = useState([])
  const [locations, setLocations] = useState([])
  const [salaryMin, setSalaryMin] = useState('')
  const [salaryMax, setSalaryMax] = useState('')
  const [workArrangement, setWorkArrangement] = useState([])
  const [recipientEmail, setRecipientEmail] = useState('')

  async function handleUpload(e) {
    e.preventDefault()
    if (!file) return
    setLoading(true)
    setError('')
    try {
      const data = await api.uploadResume(name, file)
      const ext = data.extracted || {}
      setProfile(ext)
      // Pre-fill step 2 from extracted data
      setJobTitles(ext.target_job_titles || (ext.current_job_title ? [ext.current_job_title] : []))
      setLocations(ext.preferred_locations || (ext.current_location ? [ext.current_location] : []))
      setSalaryMin(ext.salary_min_lpa ?? '')
      setSalaryMax(ext.salary_max_lpa ?? '')
      setStep(1)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  function updateProfile(field, value) {
    setProfile(prev => ({ ...prev, [field]: value }))
  }

  async function handleConfirm(e) {
    e.preventDefault()
    if (jobTitles.length === 0) { setError('Add at least one job title'); return }
    if (!recipientEmail) { setError('Recipient email is required'); return }
    setLoading(true)
    setError('')
    try {
      await api.confirmResume(name, {
        profile,
        target_job_titles: jobTitles,
        preferred_locations: locations,
        salary_min_lpa: salaryMin ? parseInt(salaryMin) : null,
        salary_max_lpa: salaryMax ? parseInt(salaryMax) : null,
        preferred_work_arrangement: workArrangement,
        recipient_email: recipientEmail,
      })
      navigate(`/profiles/${name}/dashboard`)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const arrangements = ['Remote', 'Hybrid', 'On-site']

  return (
    <div className="page">
      <div style={{ marginBottom: 8, color: 'var(--text-muted)', fontSize: 13 }}>
        <span onClick={() => navigate('/profiles')} style={{ cursor: 'pointer' }}>← Profiles</span>
        <span style={{ margin: '0 6px' }}>/</span>
        <span>{name}</span>
      </div>
      <h1 className="page-title">Profile Setup</h1>

      <StepIndicator steps={STEPS} current={step} />

      {error && <div className="alert alert-error">{error}</div>}

      {/* STEP 0: Upload */}
      {step === 0 && (
        <form onSubmit={handleUpload} className="card">
          <h2 style={{ fontSize: 16, marginBottom: 16 }}>Upload Resume</h2>
          <div
            style={{
              border: '2px dashed var(--border)', borderRadius: 10, padding: '40px 24px',
              textAlign: 'center', cursor: 'pointer', marginBottom: 16,
              background: file ? 'var(--surface2)' : 'transparent',
            }}
            onClick={() => document.getElementById('resume-input').click()}
          >
            {file ? (
              <div>
                <div style={{ fontSize: 24 }}>📄</div>
                <div style={{ marginTop: 8, fontWeight: 500 }}>{file.name}</div>
                <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>{(file.size / 1024).toFixed(0)} KB</div>
              </div>
            ) : (
              <div>
                <div style={{ fontSize: 32 }}>📤</div>
                <div style={{ marginTop: 8 }}>Click to select your resume</div>
                <div style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 4 }}>PDF or DOCX supported</div>
              </div>
            )}
          </div>
          <input id="resume-input" type="file" accept=".pdf,.docx,.doc" style={{ display: 'none' }}
            onChange={e => setFile(e.target.files[0])} />
          <button type="submit" className="btn-primary w-full" disabled={!file || loading}>
            {loading ? <><span className="spinner" style={{ marginRight: 8 }} />Extracting with AI...</> : 'Extract & Continue →'}
          </button>
        </form>
      )}

      {/* STEP 1: Verify */}
      {step === 1 && profile && (
        <form onSubmit={() => setStep(2)} className="card">
          <div className="flex justify-between items-center" style={{ marginBottom: 16 }}>
            <h2 style={{ fontSize: 16 }}>Verify Extracted Details</h2>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              Method: {profile._extraction_method || 'llm'}
            </span>
          </div>
          <div className="alert alert-info">Review and correct any wrong details before continuing.</div>

          <div className="grid-2">
            <div className="form-group">
              <label>Full Name</label>
              <input value={profile.full_name || ''} onChange={e => updateProfile('full_name', e.target.value)} />
            </div>
            <div className="form-group">
              <label>Email</label>
              <input value={profile.email || ''} onChange={e => updateProfile('email', e.target.value)} />
            </div>
            <div className="form-group">
              <label>Current Job Title</label>
              <input value={profile.current_job_title || ''} onChange={e => updateProfile('current_job_title', e.target.value)} />
            </div>
            <div className="form-group">
              <label>Total Experience (years)</label>
              <input type="number" step="0.5" min="0"
                value={profile.total_years_experience ?? ''}
                onChange={e => updateProfile('total_years_experience', parseFloat(e.target.value) || 0)} />
            </div>
            <div className="form-group">
              <label>Career Level</label>
              <select value={profile.career_level || ''} onChange={e => updateProfile('career_level', e.target.value)}>
                <option value="">Select...</option>
                {['Fresher', 'Junior', 'Mid-level', 'Senior', 'Lead', 'Manager', 'Director'].map(l => (
                  <option key={l} value={l}>{l}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Current Location</label>
              <input value={profile.current_location || ''} onChange={e => updateProfile('current_location', e.target.value)} />
            </div>
            <div className="form-group">
              <label>Industry Domain</label>
              <input value={profile.industry_domain || ''} onChange={e => updateProfile('industry_domain', e.target.value)} />
            </div>
          </div>

          <div className="form-group">
            <label>Technical Skills (press Enter to add)</label>
            <TagInput
              value={profile.technical_skills || []}
              onChange={v => updateProfile('technical_skills', v)}
              placeholder="e.g. Python, React, AWS..."
            />
          </div>

          <div className="form-group">
            <label>Soft Skills</label>
            <TagInput
              value={profile.soft_skills || []}
              onChange={v => updateProfile('soft_skills', v)}
              placeholder="e.g. Leadership, Communication..."
            />
          </div>

          <div className="flex gap-3 mt-4">
            <button type="button" className="btn-secondary" onClick={() => setStep(0)}>← Back</button>
            <button type="button" className="btn-primary" style={{ flex: 1 }} onClick={() => setStep(2)}>
              Continue →
            </button>
          </div>
        </form>
      )}

      {/* STEP 2: Preferences */}
      {step === 2 && (
        <form onSubmit={handleConfirm} className="card">
          <h2 style={{ fontSize: 16, marginBottom: 16 }}>Job Preferences</h2>

          <div className="form-group">
            <label>Target Job Titles * (press Enter to add)</label>
            <TagInput value={jobTitles} onChange={setJobTitles} placeholder="e.g. ML Engineer, Data Scientist..." />
          </div>

          <div className="form-group">
            <label>Preferred Locations (press Enter to add)</label>
            <TagInput value={locations} onChange={setLocations} placeholder="e.g. Bangalore, Remote..." />
          </div>

          <div className="grid-2">
            <div className="form-group">
              <label>Min Salary (LPA)</label>
              <input type="number" min="0" value={salaryMin} onChange={e => setSalaryMin(e.target.value)} placeholder="e.g. 12" />
            </div>
            <div className="form-group">
              <label>Max Salary (LPA)</label>
              <input type="number" min="0" value={salaryMax} onChange={e => setSalaryMax(e.target.value)} placeholder="e.g. 25" />
            </div>
          </div>

          <div className="form-group">
            <label>Work Arrangement</label>
            <div style={{ display: 'flex', gap: 12, marginTop: 6 }}>
              {arrangements.map(a => (
                <label key={a} style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', color: 'var(--text)' }}>
                  <input
                    type="checkbox"
                    style={{ width: 'auto' }}
                    checked={workArrangement.includes(a)}
                    onChange={e => setWorkArrangement(e.target.checked ? [...workArrangement, a] : workArrangement.filter(x => x !== a))}
                  />
                  {a}
                </label>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label>Recipient Email * (where to send job digests)</label>
            <input
              type="email"
              value={recipientEmail}
              onChange={e => setRecipientEmail(e.target.value)}
              placeholder="your@email.com"
              required
            />
          </div>

          <div className="flex gap-3 mt-4">
            <button type="button" className="btn-secondary" onClick={() => setStep(1)}>← Back</button>
            <button type="submit" className="btn-primary" style={{ flex: 1 }} disabled={loading}>
              {loading ? <><span className="spinner" style={{ marginRight: 8 }} />Saving...</> : 'Save & Go to Dashboard →'}
            </button>
          </div>
        </form>
      )}
    </div>
  )
}

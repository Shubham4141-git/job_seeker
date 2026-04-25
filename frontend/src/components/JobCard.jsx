export default function JobCard({ job, selected, onToggle }) {
  const m = job.match_result || {}
  const score = m.match_score ?? 0
  const scoreColor = score >= 70 ? 'var(--success)' : score >= 50 ? 'var(--warning)' : 'var(--text-muted)'

  return (
    <div className="card" style={{ borderLeft: `3px solid ${scoreColor}`, marginBottom: 12, cursor: 'pointer' }}
      onClick={() => onToggle(job)}>
      <div className="flex justify-between items-center">
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 600, fontSize: 15 }}>{job.title}</div>
          <div style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 2 }}>
            {job.company} · {job.location}
          </div>
          {job.salary_display && (
            <div style={{ fontSize: 12, color: 'var(--primary)', marginTop: 4 }}>{job.salary_display}</div>
          )}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 8, marginLeft: 16 }}>
          <div style={{
            background: 'var(--surface2)', borderRadius: 8, padding: '4px 12px',
            fontWeight: 700, fontSize: 16, color: scoreColor,
          }}>
            {score}%
          </div>
          <input type="checkbox" checked={selected} onChange={() => {}} style={{ width: 16, height: 16, cursor: 'pointer' }} />
        </div>
      </div>

      {m.matching_reasons?.length > 0 && (
        <div style={{ marginTop: 10, fontSize: 12, color: 'var(--text-muted)' }}>
          {m.matching_reasons.slice(0, 2).map((r, i) => (
            <div key={i}>✓ {r}</div>
          ))}
        </div>
      )}

      {m.missing_skills?.length > 0 && (
        <div style={{ marginTop: 6, fontSize: 12, color: 'var(--warning)' }}>
          Missing: {m.missing_skills.slice(0, 3).join(', ')}
        </div>
      )}

      <div style={{ marginTop: 10, display: 'flex', gap: 8 }}>
        <a href={job.apply_url} target="_blank" rel="noopener noreferrer"
          onClick={e => e.stopPropagation()}
          style={{ fontSize: 12, color: 'var(--primary)', background: 'var(--surface2)', borderRadius: 6, padding: '3px 10px' }}>
          Apply →
        </a>
        {m.overall_recommendation && (
          <span style={{ fontSize: 11, color: 'var(--text-muted)', alignSelf: 'center' }}>
            {m.overall_recommendation.slice(0, 80)}...
          </span>
        )}
      </div>
    </div>
  )
}

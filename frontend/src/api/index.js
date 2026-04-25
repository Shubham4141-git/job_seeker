const BASE = '/api'

async function request(method, path, body, isFile = false) {
  const opts = { method, headers: {} }
  if (body && !isFile) {
    opts.headers['Content-Type'] = 'application/json'
    opts.body = JSON.stringify(body)
  } else if (isFile) {
    opts.body = body // FormData
  }
  const res = await fetch(`${BASE}${path}`, opts)
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
  return data
}

export const api = {
  // Profiles
  getProfiles: () => request('GET', '/profiles'),
  getProfile: (name) => request('GET', `/profiles/${name}`),
  createProfile: (name) => request('POST', '/profiles', { name }),
  deleteProfile: (name) => request('DELETE', `/profiles/${name}`),

  // Resume
  uploadResume: (name, file) => {
    const fd = new FormData()
    fd.append('file', file)
    return request('POST', `/profiles/${name}/resume/upload`, fd, true)
  },
  confirmResume: (name, payload) => request('POST', `/profiles/${name}/resume/confirm`, payload),

  // Jobs
  fetchJobs: (name) => request('POST', `/profiles/${name}/jobs/fetch`),

  // Email
  sendEmail: (name, jobs) => request('POST', `/profiles/${name}/email/send`, { jobs }),
  testEmail: (name) => request('POST', `/profiles/${name}/email/test`),

  // Config status
  configStatus: () => request('GET', '/config/status'),
}
